using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace Velomux.Desktop.ViewModels;

// Wire protocol stays compatible with the existing, tested Velomux engine.
public sealed class PresetOption
{
    public string Name { get; set; } = "";
    public string Group { get; set; } = "";
    public string Ext { get; set; } = "";
}
public sealed class ProfileOption
{
    public string Id { get; set; } = "";
    public string Label { get; set; } = "";
    public string Detail { get; set; } = "";
    public string Preset { get; set; } = "";
}
public sealed class FlowOption
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string Tagline { get; set; } = "";
    public string Warning { get; set; } = "";
    public List<string> InputKinds { get; set; } = new();
    public List<ProfileOption> Profiles { get; set; } = new();
}
public sealed class CatalogOption
{
    public List<PresetOption> Presets { get; set; } = new();
    public List<FlowOption> Tasks { get; set; } = new();
    public Dictionary<string, List<string>> Suffixes { get; set; } = new();
}
public sealed class MediaJob : INotifyPropertyChanged
{
    private string _status = "Waiting", _detail = "";
    private double _progress;
    public required string Path { get; init; }
    public string? ImportRoot { get; init; }
    public string FileName => System.IO.Path.GetFileName(Path);
    public string Status
    {
        get => _status;
        set { if (_status == value) return; _status = value; Notify(); }
    }
    public string Detail
    {
        get => _detail;
        set { if (_detail == value) return; _detail = value; Notify(); }
    }
    public double Progress
    {
        get => _progress;
        set { if (Math.Abs(_progress - value) < 0.1) return; _progress = value; Notify(); }
    }
    public event PropertyChangedEventHandler? PropertyChanged;
    private void Notify([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public sealed class MainViewModel : INotifyPropertyChanged
{
    private string _status = "Initializing Velomux media engine...";
    private string _outputDirectory = System.IO.Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        "Downloads", "Velomux Converted");
    private bool _isRunning, _isCatalogLoaded, _quickMode = true, _preserveFolders = true;
    private MediaJob? _selectedJob;
    private FlowOption? _selectedTask;
    private ProfileOption? _selectedProfile;
    private PresetOption? _selectedPreset;
    private string _presetSearch = "", _presetFamily = "All";
    private string _collision = "rename", _trimStart = "0", _trimEnd = "0";
    private string _quality = "23", _imageQuality = "90", _speed = "1";
    private bool _normalize, _fullDecode;
    private string _mediaInfo = "Select a queued file and choose Inspect.";
    public ObservableCollection<MediaJob> Jobs { get; } = new();
    public ObservableCollection<FlowOption> Tasks { get; } = new();
    public ObservableCollection<ProfileOption> Profiles { get; } = new();
    public ObservableCollection<PresetOption> VisiblePresets { get; } = new();
    public ObservableCollection<string> Activity { get; } = new();
    public List<string> PresetFamilies { get; } = new() { "All", "Video", "Audio", "Image" };
    public List<string> CollisionChoices { get; } = new() { "rename", "skip", "repair", "overwrite" };
    private readonly List<PresetOption> _allPresets = new();
    private readonly HashSet<string> _knownSuffixes = new(StringComparer.OrdinalIgnoreCase);
    private readonly HashSet<string> _videoSuffixes = new(StringComparer.OrdinalIgnoreCase);
    private readonly HashSet<string> _audioSuffixes = new(StringComparer.OrdinalIgnoreCase);
    private readonly HashSet<string> _imageSuffixes = new(StringComparer.OrdinalIgnoreCase);

    public MainViewModel() => Jobs.CollectionChanged += (_, _) => RefreshQueue();
    public string Status { get => _status; set { _status = value; Notify(); } }
    public string MediaInfo { get => _mediaInfo; set { _mediaInfo = value; Notify(); } }
    public string OutputDirectory { get => _outputDirectory; set { _outputDirectory = value; Notify(); } }
    public bool PreserveFolders { get => _preserveFolders; set { _preserveFolders = value; Notify(); } }
    public bool IsRunning
    {
        get => _isRunning;
        set { _isRunning = value; Notify(); RefreshQueue(); Notify(nameof(CanAddFiles)); Notify(nameof(CanCancel)); }
    }
    public bool IsCatalogLoaded
    {
        get => _isCatalogLoaded;
        private set { _isCatalogLoaded = value; Notify(); RefreshQueue(); }
    }
    public bool CanCancel => IsRunning;
    public bool CanAddFiles => !IsRunning;
    public bool CanRemoveSelected => !IsRunning && SelectedJob != null;
    public bool CanStart => IsCatalogLoaded && !IsRunning && Jobs.Any(x => x.Status != "Completed");
    public int Queued => Jobs.Count;
    public int Completed => Jobs.Count(x => x.Status == "Completed");
    public int Failed => Jobs.Count(x => x.Status == "Failed");
    public bool IsQueueEmpty => Jobs.Count == 0;
    public bool HasQueue => Jobs.Count != 0;
    public MediaJob? SelectedJob
    {
        get => _selectedJob;
        set { _selectedJob = value; Notify(); Notify(nameof(CanRemoveSelected)); }
    }
    public bool QuickMode
    {
        get => _quickMode;
        set { if (_quickMode == value) return; _quickMode = value; Notify();
            Notify(nameof(AdvancedMode)); Notify(nameof(SelectedPresetName)); }
    }
    public bool AdvancedMode => !QuickMode;
    public FlowOption? SelectedTask
    {
        get => _selectedTask;
        set
        {
            if (ReferenceEquals(_selectedTask, value)) return;
            _selectedTask = value;
            Notify(); Notify(nameof(TaskTitle)); Notify(nameof(TaskTagline)); Notify(nameof(TaskWarning));
            Profiles.Clear();
            if (value != null)
                foreach (var p in value.Profiles) Profiles.Add(p);
            SelectedProfile = Profiles.FirstOrDefault();
            Notify(nameof(SelectedPresetName));
        }
    }
    public string TaskTitle => SelectedTask?.Title ?? "Choose a task";
    public string TaskTagline => SelectedTask?.Tagline ?? "Select what you want to do";
    public string TaskWarning => SelectedTask?.Warning ?? "";
    public ProfileOption? SelectedProfile
    {
        get => _selectedProfile;
        set { _selectedProfile = value; Notify(); Notify(nameof(ProfileDetail)); Notify(nameof(SelectedPresetName)); }
    }
    public string ProfileDetail => SelectedProfile?.Detail ?? "";
    public PresetOption? SelectedPreset
    {
        get => _selectedPreset;
        set { _selectedPreset = value; Notify(); Notify(nameof(SelectedPresetName)); }
    }
    public string SelectedPresetName => QuickMode
        ? SelectedProfile?.Preset ?? ""
        : SelectedPreset?.Name ?? "";
    public string PresetSearch
    {
        get => _presetSearch;
        set { _presetSearch = value; Notify(); FilterPresets(); }
    }
    public string PresetFamily
    {
        get => _presetFamily;
        set { _presetFamily = value; Notify(); FilterPresets(); }
    }
    public string Collision
    {
        get => _collision;
        set { _collision = value; Notify(); }
    }
    public string TrimStart { get => _trimStart; set { _trimStart = value; Notify(); } }
    public string TrimEnd { get => _trimEnd; set { _trimEnd = value; Notify(); } }
    public string Quality { get => _quality; set { _quality = value; Notify(); } }
    public string ImageQuality { get => _imageQuality; set { _imageQuality = value; Notify(); } }
    public string Speed { get => _speed; set { _speed = value; Notify(); } }
    public bool Normalize { get => _normalize; set { _normalize = value; Notify(); } }
    public bool FullDecode { get => _fullDecode; set { _fullDecode = value; Notify(); } }

    public void SetCatalog(CatalogOption catalog)
    {
        if (catalog.Presets.Count != 51 || catalog.Tasks.Count != 7 ||
            catalog.Tasks.Sum(t => t.Profiles.Count) != 29)
            throw new InvalidDataException("The packaged engine catalog does not match the 51 presets and 29 approved VeloFlow profiles.");
        var actual = catalog.Presets.Select(x => x.Name).ToHashSet(StringComparer.Ordinal);
        if (catalog.Tasks.SelectMany(t => t.Profiles).Any(p => !actual.Contains(p.Preset)))
            throw new InvalidDataException("A selected VeloFlow profile references a missing encoder preset.");
        Tasks.Clear(); _allPresets.Clear();
        foreach (var p in catalog.Presets) _allPresets.Add(p);
        foreach (var t in catalog.Tasks) Tasks.Add(t);
        foreach (var suffix in catalog.Suffixes)
        {
            HashSet<string> set = suffix.Key switch
            {
                "video" => _videoSuffixes, "audio" => _audioSuffixes,
                "image" => _imageSuffixes, _ => new HashSet<string>()
            };
            foreach (var x in suffix.Value) { set.Add(x); _knownSuffixes.Add(x); }
        }
        SelectedTask = Tasks.FirstOrDefault(x => x.Id == "video");
        FilterPresets();
        IsCatalogLoaded = true;
        Status = $"Engine ready · {Tasks.Count} workflows · {catalog.Tasks.Sum(t=>t.Profiles.Count)} quick profiles · {catalog.Presets.Count} advanced presets.";
    }
    public void ChooseTask(string id)
    {
        var candidate = Tasks.FirstOrDefault(x => x.Id == id);
        if (candidate != null) { QuickMode = true; SelectedTask = candidate; }
    }
    private void FilterPresets()
    {
        var prior = SelectedPreset?.Name;
        VisiblePresets.Clear();
        foreach (var item in _allPresets)
        {
            if (PresetFamily != "All" &&
                !string.Equals(item.Group, PresetFamily, StringComparison.OrdinalIgnoreCase)) continue;
            if (!item.Name.Contains(PresetSearch ?? "", StringComparison.OrdinalIgnoreCase)) continue;
            VisiblePresets.Add(item);
        }
        SelectedPreset = VisiblePresets.FirstOrDefault(x => x.Name == prior) ??
                         VisiblePresets.FirstOrDefault();
    }
    public string Classify(string file)
    {
        string ext = System.IO.Path.GetExtension(file);
        if (_videoSuffixes.Contains(ext)) return "video";
        if (_audioSuffixes.Contains(ext)) return "audio";
        if (_imageSuffixes.Contains(ext)) return "image";
        return "";
    }
    public bool Compatible(string file)
    {
        string kind = Classify(file);
        if (QuickMode) return SelectedTask?.InputKinds.Contains(kind) == true;
        var group = SelectedPreset?.Group ?? "";
        return group == "image" ? kind == "image"
            : group == "video" ? kind == "video"
            : group == "audio" && (kind == "video" || kind == "audio");
    }
    public void AddFiles(IEnumerable<string> paths, string? root = null)
    {
        if (IsRunning) return;
        int added = 0, ignored = 0;
        var seen = Jobs.Select(j => System.IO.Path.GetFullPath(j.Path))
            .ToHashSet(OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);
        foreach (var path in paths)
        {
            if (!File.Exists(path) || !_knownSuffixes.Contains(System.IO.Path.GetExtension(path)))
            { ignored++; continue; }
            var full = System.IO.Path.GetFullPath(path);
            if (seen.Add(full))
            {
                Jobs.Add(new MediaJob { Path = full, ImportRoot = root });
                added++;
            }
        }
        if (added > 0) AddActivity($"Added {added} file(s)" + (ignored > 0 ? $"; ignored {ignored}" : "") + ".");
        else if (ignored > 0) Status = $"No supported files added ({ignored} incompatible).";
    }
    public void RemoveSelected()
    {
        if (!CanRemoveSelected || SelectedJob == null) return;
        Jobs.Remove(SelectedJob);
        SelectedJob = null;
    }
    public void ClearCompleted()
    {
        if (IsRunning) return;
        foreach (var j in Jobs.Where(x => x.Status == "Completed" || x.Status == "Skipped").ToList())
            Jobs.Remove(j);
    }
    public void AddActivity(string message)
    {
        Activity.Insert(0, DateTime.Now.ToString("HH:mm:ss") + "  " + message);
        while (Activity.Count > 150) Activity.RemoveAt(Activity.Count - 1);
        Status = message;
    }
    public void RefreshQueue()
    {
        foreach (var name in new[] { nameof(Queued), nameof(Completed), nameof(Failed),
            nameof(CanStart), nameof(HasQueue), nameof(IsQueueEmpty), nameof(CanRemoveSelected) })
            Notify(name);
    }
    public event PropertyChangedEventHandler? PropertyChanged;
    private void Notify([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
