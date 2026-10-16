using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace Velomux.Desktop.ViewModels;

public enum AudioOutputFormat { M4a, Mp3 }

public sealed class MediaQueueItem : INotifyPropertyChanged
{
    private string _status = "Waiting";
    private string _detail = "";

    public required string Path { get; init; }
    public string FileName => System.IO.Path.GetFileName(Path);
    public string Status
    {
        get => _status;
        set { if (_status == value) return; _status = value; Changed(); }
    }
    public string Detail
    {
        get => _detail;
        set { if (_detail == value) return; _detail = value; Changed(); }
    }
    public event PropertyChangedEventHandler? PropertyChanged;
    private void Changed([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public sealed class MainViewModel : INotifyPropertyChanged
{
    private static readonly HashSet<string> Supported = new(StringComparer.OrdinalIgnoreCase)
    {
        ".mp4", ".mkv", ".mov", ".webm", ".avi", ".mp3", ".m4a", ".aac",
        ".flac", ".wav", ".ogg", ".opus"
    };

    private string _status = "Ready. Media stays on your computer.";
    private AudioOutputFormat _format = AudioOutputFormat.M4a;
    private string _outputDirectory = System.IO.Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        "Downloads", "Velomux Converted");
    private bool _isRunning;
    private MediaQueueItem? _selectedJob;

    public ObservableCollection<MediaQueueItem> Jobs { get; } = new();

    public MainViewModel()
    {
        Jobs.CollectionChanged += (_, _) =>
        {
            Changed(nameof(Queued));
            Changed(nameof(CanStart));
        };
    }

    public string Status { get => _status; set { _status = value; Changed(); } }
    public string OutputDirectory
    {
        get => _outputDirectory;
        set { _outputDirectory = value; Changed(); }
    }
    public bool IsRunning
    {
        get => _isRunning;
        set
        {
            _isRunning = value;
            Changed();
            Changed(nameof(CanStart));
            Changed(nameof(CanCancel));
        }
    }
    public bool CanCancel => IsRunning;
    public bool CanStart => !IsRunning && Jobs.Any(j => j.Status != "Completed");
    public int Queued => Jobs.Count;
    public int Completed => Jobs.Count(j => j.Status == "Completed");
    public int Failed => Jobs.Count(j => j.Status == "Failed");
    public MediaQueueItem? SelectedJob
    {
        get => _selectedJob;
        set { _selectedJob = value; Changed(); }
    }
    public AudioOutputFormat Format
    {
        get => _format;
        set
        {
            _format = value;
            Changed();
            Changed(nameof(IsM4a));
            Changed(nameof(IsMp3));
            Changed(nameof(FormatDescription));
        }
    }
    public bool IsM4a => Format == AudioOutputFormat.M4a;
    public bool IsMp3 => Format == AudioOutputFormat.Mp3;
    public string FormatDescription => Format == AudioOutputFormat.M4a
        ? "M4A · AAC 192 kbps · extracts the first audio track"
        : "MP3 · 192 kbps · extracts the first audio track";

    public void AddFiles(IEnumerable<string> paths)
    {
        var seen = Jobs.Select(j => System.IO.Path.GetFullPath(j.Path))
            .ToHashSet(OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);
        int added = 0, ignored = 0;
        foreach (var path in paths)
        {
            if (!File.Exists(path) || !Supported.Contains(System.IO.Path.GetExtension(path)))
            {
                ignored++;
                continue;
            }
            var full = System.IO.Path.GetFullPath(path);
            if (seen.Add(full))
            {
                Jobs.Add(new MediaQueueItem { Path = full });
                added++;
            }
        }
        Status = $"Added {added} audio-capable media file(s)."
               + (ignored > 0 ? $" Ignored {ignored} unsupported input(s)." : "");
    }

    public void RemoveSelected()
    {
        if (IsRunning || SelectedJob is null) return;
        Jobs.Remove(SelectedJob);
        SelectedJob = null;
    }

    public void NotifyFinished()
    {
        Changed(nameof(Completed));
        Changed(nameof(Failed));
        Changed(nameof(CanStart));
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void Changed([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
