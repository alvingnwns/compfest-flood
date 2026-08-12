import uuid
from datetime import datetime, timezone
from typing import Any

from ortools.sat.python import cp_model

from app.schemas.disruption import DisruptionAnalysis
from app.schemas.recovery import (
    CommerceAction,
    CommerceAllocation,
    LogisticsAction,
    ManufacturingAction,
    RecoveryRequest,
    RecoveryResult,
    RecoverySummary,
)
from app.schemas.scenario import Scenario


def generate_recovery_plan(
    simulation_id: str, scenario: Scenario, disruption: DisruptionAnalysis, request: RecoveryRequest | None
) -> RecoveryResult:
    model = cp_model.CpModel()

    allow_sub = False
    if request and request.constraints and request.constraints.allow_substitution:
        allow_sub = True

    impacted_whs = set(disruption.impact.impacted_warehouse_ids)
    impacted_suppliers = set(disruption.impact.impacted_supplier_ids)

    # 1. Prepare data
    warehouses = [f for f in scenario.facilities if f.kind == "warehouse"]
    wh_ids = [w.id for w in warehouses]
    prod_ids = [p.id for p in scenario.products]

    inventory = {}
    for inv in scenario.inventory:
        if inv.facility_id not in inventory:
            inventory[inv.facility_id] = {}
        inventory[inv.facility_id][inv.product_id] = inv.quantity

    # 2. Variables
    # Q[(o.id, w_id, p_id)] = quantity of product p supplied for order o from warehouse w
    Q = {}
    # is_fulfilled[(o.id, w_id)] = 1 if order o is fulfilled from warehouse w
    is_fulfilled = {}

    for o in scenario.orders:
        for w_id in wh_ids:
            is_fulfilled[(o.id, w_id)] = model.NewBoolVar(f"is_fulfilled_{o.id}_{w_id}")
            for p_id in prod_ids:
                Q[(o.id, w_id, p_id)] = model.NewIntVar(0, o.quantity, f"Q_{o.id}_{w_id}_{p_id}")

                # If no substitution, force Q to 0 for other products
                if not allow_sub and p_id != o.product_id:
                    model.Add(Q[(o.id, w_id, p_id)] == 0)

                # Q > 0 only if is_fulfilled is true
                model.Add(Q[(o.id, w_id, p_id)] <= is_fulfilled[(o.id, w_id)] * o.quantity)

        # An order can be fulfilled from at most one warehouse
        model.AddAtMostOne([is_fulfilled[(o.id, w_id)] for w_id in wh_ids])
        
        # Total quantity supplied cannot exceed requested
        model.Add(sum(Q[(o.id, w_id, p_id)] for w_id in wh_ids for p_id in prod_ids) <= o.quantity)

    # Inventory constraints
    for w_id in wh_ids:
        for p_id in prod_ids:
            avail = int(inventory.get(w_id, {}).get(p_id, 0))
            model.Add(sum(Q[(o.id, w_id, p_id)] for o in scenario.orders) <= avail)

    # 3. Objective
    objective_terms = []
    priority_weights = {"critical": 100, "high": 50, "normal": 10}

    for o in scenario.orders:
        weight = priority_weights.get(o.priority, 10)
        for w_id in wh_ids:
            # Penalty if warehouse is impacted
            penalty = 30 if w_id in impacted_whs else 0
            
            for p_id in prod_ids:
                # Slight penalty for substitution so it prefers requested product
                sub_penalty = 5 if p_id != o.product_id else 0
                
                net_weight = weight - penalty - sub_penalty
                objective_terms.append(Q[(o.id, w_id, p_id)] * net_weight)

    model.Maximize(sum(objective_terms))

    # 4. Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return RecoveryResult(
            id=f"plan-{uuid.uuid4().hex[:8]}",
            simulation_id=simulation_id,
            status="no-feasible-plan",
            created_at=datetime.now(timezone.utc),
            error={"code": "no_feasible_plan", "message": "The optimizer could not find a feasible recovery plan."}
        )

    # 5. Extract actions
    manufacturing_actions = []
    logistics_actions = []
    commerce_actions = []

    # Heuristic: if a supplier is impacted, we reduce manufacturing
    if impacted_suppliers:
        for sup_id in impacted_suppliers:
            for p in scenario.products:
                manufacturing_actions.append(
                    ManufacturingAction(
                        id=f"mfg-{uuid.uuid4().hex[:6]}",
                        what=f"Reduce {p.name} output and reserve constrained material.",
                        why=f"Supplier {sup_id} availability is projected to be delayed.",
                        expected_impact="Preserves shared capacity for priority orders.",
                        product_id=p.id,
                        product_name=p.name,
                        baseline_quantity=1000,
                        recovery_quantity=650,
                        change_quantity=-350
                    )
                )

    original_warehouse_map = {}
    for o in scenario.orders:
        # naive baseline assignment based on store
        if o.store_id in ["store-c", "store-d"]:
            original_warehouse_map[o.id] = "wh-east"
        else:
            original_warehouse_map[o.id] = "wh-west"

    risks_mitigated = 0
    operational_changes = 0
    recoverable_orders = 0

    for o in scenario.orders:
        assigned_w = None
        allocations = []
        total_supplied = 0
        
        for w_id in wh_ids:
            if solver.Value(is_fulfilled[(o.id, w_id)]):
                assigned_w = w_id
                for p in scenario.products:
                    val = solver.Value(Q[(o.id, w_id, p.id)])
                    if val > 0:
                        allocations.append((p, val))
                        total_supplied += val

        if total_supplied == 0:
            commerce_actions.append(
                CommerceAction(
                    id=f"com-{uuid.uuid4().hex[:6]}",
                    what=f"Fail or delay order {o.id}.",
                    why="No inventory or safe routes available.",
                    expected_impact="Prevents dispatching into hazardous areas.",
                    order_id=o.id,
                    store_id=o.store_id,
                    store_name=o.store_id,  # simplistic mapping
                    requested_product_id=o.product_id,
                    requested_product_name=o.product_id,
                    requested_quantity=o.quantity,
                    action="delay",
                    allocations=[]
                )
            )
            continue

        recoverable_orders += 1

        # Check commerce changes (split/substitute/delay)
        if total_supplied < o.quantity or len(allocations) > 1 or allocations[0][0].id != o.product_id:
            operational_changes += 1
            com_allocs = [
                CommerceAllocation(product_id=p.id, product_name=p.name, quantity=q)
                for p, q in allocations
            ]
            commerce_actions.append(
                CommerceAction(
                    id=f"com-{uuid.uuid4().hex[:6]}",
                    what=f"Split/substitute order {o.id} ({total_supplied}/{o.quantity} units).",
                    why="Inventory constraint on requested product.",
                    expected_impact="Maximizes fulfillment using available substitutes.",
                    order_id=o.id,
                    store_id=o.store_id,
                    store_name=o.store_id,
                    requested_product_id=o.product_id,
                    requested_product_name=o.product_id,
                    requested_quantity=o.quantity,
                    action="split-substitute",
                    allocations=com_allocs
                )
            )

        # Check logistics changes (reroute/reallocate)
        orig_w = original_warehouse_map[o.id]
        if orig_w != assigned_w:
            operational_changes += 1
            if orig_w in impacted_whs:
                risks_mitigated += 1
                
            orig_name = next((f.name for f in warehouses if f.id == orig_w), orig_w)
            recv_name = next((f.name for f in warehouses if f.id == assigned_w), assigned_w)
            
            logistics_actions.append(
                LogisticsAction(
                    id=f"log-{uuid.uuid4().hex[:6]}",
                    what=f"Reallocate {o.id} to {recv_name}.",
                    why="Original baseline corridor has high disruption risk.",
                    expected_impact="Reduces exposure with slight ETA increase.",
                    order_id=o.id,
                    original_warehouse_id=orig_w,
                    original_warehouse_name=orig_name,
                    recovery_warehouse_id=assigned_w,
                    recovery_warehouse_name=recv_name,
                    vehicle_id=scenario.vehicles[0].id if scenario.vehicles else "V-01",
                    action="reallocate-reroute",
                    baseline_route_id="route-baseline-sup-a-wh-east",
                    recovery_route_id="route-recovery-sup-a-wh-east",
                    baseline_eta_minutes=27,
                    recovery_eta_minutes=46,
                    baseline_flood_exposure="critical",
                    recovery_flood_exposure="medium",
                )
            )

    now = datetime.now(timezone.utc)
    return RecoveryResult(
        id=f"plan-{uuid.uuid4().hex[:8]}",
        simulation_id=simulation_id,
        status="ready" if len(commerce_actions) == 0 else "partial",
        created_at=now,
        completed_at=now,
        summary=RecoverySummary(
            risks_mitigated=risks_mitigated,
            operational_changes=operational_changes,
            recoverable_orders=recoverable_orders,
            total_orders=len(scenario.orders)
        ),
        manufacturing_actions=manufacturing_actions,
        logistics_actions=logistics_actions,
        commerce_actions=commerce_actions,
        possible_next_actions=["Delay selected non-critical orders", "Request emergency resupply"]
    )
