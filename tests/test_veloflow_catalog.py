"""VeloFlow contract: task names must map to real presets and real input kinds."""
from pathlib import Path

from engine import PRESET_MAP
from velomux_flows import (
    FLOWS, FLOWS_BY_ID, PROFILE_BY_ID, AUTOMATIC_BY_KIND,
    destination_for, recommended_preset,
)


def test_every_curated_profile_points_to_supported_existing_engine_preset():
    task_ids = [t.id for t in FLOWS]
    profile_ids = [p.id for t in FLOWS for p in t.profiles]
    assert len(FLOWS) >= 7
    assert len(task_ids) == len(set(task_ids))
    assert len(profile_ids) == len(set(profile_ids))
    assert {'video','audio','images','extract','compress','rewrap','trim'} <= set(task_ids)
    assert len(profile_ids) >= 24
    for task in FLOWS:
        assert task.profiles and task.input_kinds
        for p in task.profiles:
            assert p.preset in PRESET_MAP
            assert PROFILE_BY_ID[p.id] == p
            engine_preset = PRESET_MAP[p.preset]
            if task.id in ('video','compress','rewrap','trim'):
                assert engine_preset.group == 'video'
            elif task.id in ('extract','audio'):
                assert engine_preset.group == 'audio'
            else:
                assert engine_preset.group == 'image'


def test_import_defaults_do_not_silently_turn_video_into_m4a():
    assert AUTOMATIC_BY_KIND['video'] != 'M4A - AAC (smart copy)'
    assert PRESET_MAP[recommended_preset('video')].group == 'video'
    assert PRESET_MAP[recommended_preset('audio')].group == 'audio'
    assert PRESET_MAP[recommended_preset('image')].group == 'image'


def test_explicit_quick_tasks_never_silently_use_incompatible_inputs():
    for task in FLOWS:
        first = task.profiles[0]
        for kind in ('video', 'audio', 'image'):
            suggestion = recommended_preset(kind, task.id, first.id)
            assert (suggestion is not None) == (kind in task.input_kinds)
        assert recommended_preset(task.input_kinds[0], task.id, 'not-a-valid-profile') is None
        assert recommended_preset(task.input_kinds[0], 'not-a-task') is None


def test_extract_is_explicit_and_copy_is_not_same_as_reencode():
    preset = recommended_preset('video', 'extract', 'extract-m4a')
    assert PRESET_MAP[preset].smart_copy
    assert recommended_preset('video', 'audio') is None
    fast = PRESET_MAP[recommended_preset('video','trim','trim-quick')]
    precise = PRESET_MAP[recommended_preset('video','trim','trim-accurate')]
    assert fast.vcodec == 'copy'
    assert precise.vcodec == 'libx264'


def test_batch_folder_preservation_and_fallback(tmp_path):
    root = tmp_path/'Music Library'
    file = root/'90s'/'Jhankar'/'Song.mp4'
    output = tmp_path/'Converted'
    assert destination_for(file, output, root, True) == output/'90s'/'Jhankar'
    assert destination_for(file, output, root, False) == output
    assert destination_for(file, output, None, True) == output
    assert destination_for(file, output, tmp_path/'Other', True) == output
    assert destination_for(root/'Album'/'Song.flac', output, root, True) == output/'Album'


def test_curated_profiles_have_meaningful_distinct_options():
    task = FLOWS_BY_ID['images']
    options = {PRESET_MAP[p.preset].ext for p in task.profiles}
    assert {'.jpg', '.png', '.webp'} <= options
    assert 'WebP - Lossless' in [p.preset for p in task.profiles]
    task = FLOWS_BY_ID['video']
    assert any(PRESET_MAP[p.preset].video_quality_hint == 18 for p in task.profiles)
    assert any(PRESET_MAP[p.preset].video_speed_hint for p in task.profiles)
