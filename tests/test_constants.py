from sector_rotation.src.constants import SECTORS, SECTOR_NAME_MAP


def test_sectors_contains_expected_keys():
    assert "Technology" in SECTORS
    assert SECTORS["Technology"] == "XLK"
    assert "Energy" in SECTORS
    assert len(SECTORS) >= 10


def test_sector_name_map_translates():
    assert SECTOR_NAME_MAP["Technology"] == "Information Technology"
    assert SECTOR_NAME_MAP.get("Energy") is None
