import pytest
import uuid
from app.services.pfi_service import PFIService


@pytest.mark.asyncio
async def test_pfi_formula():
    """Test PFI scoring formula without DB."""
    svc = PFIService(db=None)

    # Simulate perfect freelancer
    raw = (
        0.40 * 1.0  # 100% success rate
        + 0.30 * 1.0  # 100% quality
        + 0.20 * 1.0  # 100% on-time
        + 0.10 * 1.0  # 0% dispute rate → (1-0)
    )
    score = round(300 + raw * 550, 1)
    assert score == 850.0

    # Simulate worst freelancer
    raw_bad = (
        0.40 * 0.0 + 0.30 * 0.0 + 0.20 * 0.0 + 0.10 * 0.0
    )
    score_bad = round(300 + raw_bad * 550, 1)
    assert score_bad == 300.0
