from app.services.flood_risk_service import predict_risk

def test_predict_risk_high_hazard():
    props = {
        "travelTimeMinutes": 15.0,
        "rainfallMm": 200.0,
        "hazardScore": 0.95,
        "elevationMeters": 1.0,
        "historicalFloodExposure": 0.8,
        "drainagePressure": 0.9
    }
    result = predict_risk(props)
    assert 0.0 <= result.riskProbability <= 1.0
    assert result.riskLevel in ["low", "medium", "high", "critical"]
    assert result.estimatedDelayMinutes >= 15
    assert len(result.riskFactors) >= 1

def test_predict_risk_low_hazard():
    props = {
        "travelTimeMinutes": 10.0,
        "rainfallMm": 20.0,
        "hazardScore": 0.1,
        "elevationMeters": 15.0,
        "historicalFloodExposure": 0.0,
        "drainagePressure": 0.1
    }
    result = predict_risk(props)
    assert 0.0 <= result.riskProbability <= 1.0
    assert result.riskLevel in ["low", "medium", "high", "critical"]
    assert result.estimatedDelayMinutes >= 0
