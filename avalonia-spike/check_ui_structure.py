"""Static structural check for the narrow Avalonia evaluation interface."""
from pathlib import Path
from xml.etree import ElementTree as ET

folder = Path(__file__).resolve().parent
ui = ET.parse(folder / "Velomux.Desktop" / "MainWindow.axaml")
elements = [n.tag.rsplit("}", 1)[-1] for n in ui.iter()]
assert elements.count("ScrollViewer") == 1, "Nested settings scrolling is not allowed."
for forbidden in ("TabControl", "TabItem", "TabStrip", "NumericUpDown", "ComboBox"):
    assert forbidden not in elements, f"Wheel-driven UI control found: {forbidden}"
assert "ListBox" in elements, "The user needs a real selectable file queue."
engine = (folder / "Velomux.Desktop" / "Services" /
          "AudioConversionService.cs").read_text(encoding="utf-8")
for token in ("ArgumentList.Add", "File.Move(staged, output, overwrite: false)",
              "WaitForExitAsync", "VerifyAudioAsync", "Kill(entireProcessTree: true)"):
    assert token in engine, f"Missing media safety contract: {token}"
assert "UseShellExecute = false" in engine
print("PASS: one settings scroll, zero tabs/spinners, staged FFmpeg extraction.")
