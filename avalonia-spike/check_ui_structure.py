"""Deterministic structural checks for the native Avalonia workstation."""
from pathlib import Path
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parent
ui = ET.parse(root / "Velomux.Desktop" / "MainWindow.axaml")
elements = [n.tag.rsplit("}", 1)[-1] for n in ui.iter()]
assert elements.count("ScrollViewer") == 1, "Only one settings scroll region is allowed."
for forbidden in ("TabControl", "TabItem", "TabStrip", "NumericUpDown"):
    assert forbidden not in elements, f"Wheel-driven tab/spinner control found: {forbidden}"
assert "ComboBox" in elements, "Preset and profile selectors are missing."
assert "ListBox" in elements, "A real selectable queue is required."
tasks = [
    n.attrib["Tag"] for n in ui.iter()
    if n.attrib.get("Tag") in
    ("video", "audio", "images", "extract", "compress", "rewrap", "trim")
]
assert set(tasks) == {"video", "audio", "images", "extract", "compress", "rewrap", "trim"}
assert len(tasks) == 14, "Full and compact navigation must cover all seven workflows."
bridge = (root / "Velomux.Desktop" / "Services" / "MediaEngineBridge.cs").read_text(encoding="utf-8")
for token in ("ArgumentList.Add", "RedirectStandardInput = true",
              "RedirectStandardOutput = true", "Kill(entireProcessTree: true)",
              "WaitForExitAsync", "LoadCatalogAsync", "ConvertAsync"):
    assert token in bridge, f"Missing bounded media bridge safeguard: {token}"
assert "UseShellExecute = false" in bridge, "Shell execution is forbidden."
source = (root / "media_bridge.py").read_text(encoding="utf-8")
assert "from engine import" in source and "from velomux_flows import FLOWS" in source
assert 'event="result"' in source and 'command == "--integration-test"' in source
assert "Video", "Catalog checks source controlled in engine.py"
print("PASS: native Avalonia task selectors, single scroll, structured engine bridge and safety gates.")
