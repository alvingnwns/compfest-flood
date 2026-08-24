from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(values, -30, 30)))


@dataclass
class RecurrentTrainingResult:
    estimator: NumpyRecurrentClassifier
    best_epoch: int
    epochs_run: int
    best_validation_loss: float


class NumpyRecurrentClassifier:
    """Small full-batch GRU/LSTM classifier with deterministic NumPy BPTT."""

    def __init__(
        self,
        cell: str,
        input_size: int,
        hidden_size: int,
        *,
        seed: int = 42,
        learning_rate: float = 0.01,
        l2: float = 1e-4,
    ) -> None:
        if cell not in {"gru", "lstm"}:
            raise ValueError("cell must be gru or lstm")
        self.cell = cell
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.seed = seed
        self.learning_rate = learning_rate
        self.l2 = l2
        rng = np.random.default_rng(seed)
        scale = 1 / np.sqrt(input_size + hidden_size)
        gates = 3 if cell == "gru" else 4
        self.W = rng.normal(0, scale, size=(input_size + hidden_size, gates * hidden_size))
        self.b = np.zeros(gates * hidden_size)
        self.output_weight = rng.normal(0, 1 / np.sqrt(hidden_size), size=hidden_size)
        self.output_bias = 0.0

    def _forward(self, X: np.ndarray, *, cache: bool = False) -> tuple[np.ndarray, list[tuple]]:
        batch = len(X)
        hidden = np.zeros((batch, self.hidden_size))
        cell_state = np.zeros_like(hidden)
        states: list[tuple] = []
        for step in range(X.shape[1]):
            previous_hidden = hidden
            joined = np.concatenate([X[:, step, :], previous_hidden], axis=1)
            if self.cell == "gru":
                gate_values = joined @ self.W + self.b
                z = _sigmoid(gate_values[:, : self.hidden_size])
                r = _sigmoid(gate_values[:, self.hidden_size : 2 * self.hidden_size])
                candidate_input = np.concatenate([X[:, step, :], r * previous_hidden], axis=1)
                candidate = np.tanh(
                    candidate_input @ self.W[:, 2 * self.hidden_size :] + self.b[2 * self.hidden_size :]
                )
                hidden = (1 - z) * candidate + z * previous_hidden
                if cache:
                    states.append((joined, candidate_input, previous_hidden, z, r, candidate))
            else:
                gates = joined @ self.W + self.b
                i = _sigmoid(gates[:, : self.hidden_size])
                f = _sigmoid(gates[:, self.hidden_size : 2 * self.hidden_size])
                o = _sigmoid(gates[:, 2 * self.hidden_size : 3 * self.hidden_size])
                candidate = np.tanh(gates[:, 3 * self.hidden_size :])
                previous_cell = cell_state
                cell_state = f * previous_cell + i * candidate
                hidden = o * np.tanh(cell_state)
                if cache:
                    states.append((joined, previous_hidden, previous_cell, cell_state, i, f, o, candidate))
        return _sigmoid(hidden @ self.output_weight + self.output_bias), states

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        probability, _ = self._forward(np.asarray(X, dtype=np.float64))
        return np.column_stack([1 - probability, probability])

    def _loss(self, X: np.ndarray, y: np.ndarray, sample_weight: np.ndarray) -> float:
        probability, _ = self._forward(X)
        probability = np.clip(probability, 1e-8, 1 - 1e-8)
        data_loss = -np.mean(sample_weight * (y * np.log(probability) + (1 - y) * np.log(1 - probability)))
        return float(data_loss + 0.5 * self.l2 * (np.sum(self.W**2) + np.sum(self.output_weight**2)))

    def _gradients(self, X: np.ndarray, y: np.ndarray, sample_weight: np.ndarray) -> list[np.ndarray | float]:
        probability, states = self._forward(X, cache=True)
        final_hidden = (
            (1 - states[-1][3]) * states[-1][5] + states[-1][3] * states[-1][2]
            if self.cell == "gru"
            else states[-1][6] * np.tanh(states[-1][3])
        )
        output_delta = sample_weight * (probability - y) / len(y)
        grad_output_weight = final_hidden.T @ output_delta + self.l2 * self.output_weight
        grad_output_bias = float(np.sum(output_delta))
        grad_W = np.zeros_like(self.W)
        grad_b = np.zeros_like(self.b)
        grad_hidden = output_delta[:, None] * self.output_weight[None, :]
        grad_cell = np.zeros_like(grad_hidden)

        for state in reversed(states):
            if self.cell == "gru":
                joined, candidate_input, previous_hidden, z, r, candidate = state
                grad_candidate = grad_hidden * (1 - z)
                grad_z = grad_hidden * (previous_hidden - candidate)
                grad_previous = grad_hidden * z
                delta_candidate = grad_candidate * (1 - candidate**2)
                candidate_W = self.W[:, 2 * self.hidden_size :]
                grad_W[:, 2 * self.hidden_size :] += candidate_input.T @ delta_candidate
                grad_b[2 * self.hidden_size :] += delta_candidate.sum(axis=0)
                grad_candidate_input = delta_candidate @ candidate_W.T
                grad_r = grad_candidate_input[:, self.input_size :] * previous_hidden
                grad_previous += grad_candidate_input[:, self.input_size :] * r
                delta_r = grad_r * r * (1 - r)
                grad_W[:, self.hidden_size : 2 * self.hidden_size] += joined.T @ delta_r
                grad_b[self.hidden_size : 2 * self.hidden_size] += delta_r.sum(axis=0)
                grad_previous += (delta_r @ self.W[:, self.hidden_size : 2 * self.hidden_size].T)[:, self.input_size :]
                delta_z = grad_z * z * (1 - z)
                grad_W[:, : self.hidden_size] += joined.T @ delta_z
                grad_b[: self.hidden_size] += delta_z.sum(axis=0)
                grad_previous += (delta_z @ self.W[:, : self.hidden_size].T)[:, self.input_size :]
                grad_hidden = grad_previous
            else:
                joined, _, previous_cell, cell_state, i, f, o, candidate = state
                tanh_cell = np.tanh(cell_state)
                grad_o = grad_hidden * tanh_cell
                grad_cell += grad_hidden * o * (1 - tanh_cell**2)
                grad_f = grad_cell * previous_cell
                grad_i = grad_cell * candidate
                grad_candidate = grad_cell * i
                grad_previous_cell = grad_cell * f
                deltas = np.concatenate(
                    [
                        grad_i * i * (1 - i),
                        grad_f * f * (1 - f),
                        grad_o * o * (1 - o),
                        grad_candidate * (1 - candidate**2),
                    ],
                    axis=1,
                )
                grad_W += joined.T @ deltas
                grad_b += deltas.sum(axis=0)
                grad_hidden = (deltas @ self.W.T)[:, self.input_size :]
                grad_cell = grad_previous_cell
        grad_W += self.l2 * self.W
        gradients: list[np.ndarray | float] = [grad_W, grad_b, grad_output_weight, grad_output_bias]
        total_norm = np.sqrt(sum(float(np.sum(np.asarray(value) ** 2)) for value in gradients))
        if total_norm > 5:
            gradients = [np.asarray(value) * (5 / total_norm) for value in gradients]
        return gradients

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        validation_X: np.ndarray,
        validation_y: np.ndarray,
        sample_weight: np.ndarray,
        *,
        max_epochs: int = 250,
        patience: int = 30,
    ) -> RecurrentTrainingResult:
        parameters = [self.W, self.b, self.output_weight, np.asarray(self.output_bias)]
        first_moments = [np.zeros_like(value) for value in parameters]
        second_moments = [np.zeros_like(value) for value in parameters]
        best = [value.copy() for value in parameters]
        best_loss = float("inf")
        best_epoch = 0
        stale = 0
        validation_weight = np.ones(len(validation_y))
        epochs_run = 0
        for epoch in range(1, max_epochs + 1):
            gradients = self._gradients(X, y, sample_weight)
            for index, (parameter, gradient) in enumerate(zip(parameters, gradients, strict=True)):
                gradient_array = np.asarray(gradient)
                first_moments[index] = 0.9 * first_moments[index] + 0.1 * gradient_array
                second_moments[index] = 0.999 * second_moments[index] + 0.001 * gradient_array**2
                corrected_first = first_moments[index] / (1 - 0.9**epoch)
                corrected_second = second_moments[index] / (1 - 0.999**epoch)
                parameter -= self.learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
            self.output_bias = float(parameters[3])
            validation_loss = self._loss(validation_X, validation_y, validation_weight)
            epochs_run = epoch
            if validation_loss < best_loss - 1e-6:
                best_loss = validation_loss
                best_epoch = epoch
                best = [value.copy() for value in parameters]
                stale = 0
            else:
                stale += 1
            if stale >= patience:
                break
        self.W, self.b, self.output_weight = (best[0], best[1], best[2])
        self.output_bias = float(best[3])
        return RecurrentTrainingResult(self, best_epoch, epochs_run, best_loss)
