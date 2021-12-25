import abc
import enum


class CorePlatformType(enum.Enum):
    MacOsAmd64 = enum.auto()
    MacOsArm64 = enum.auto()
    WindowsX86 = enum.auto()
    WindowsAmd64 = enum.auto()
    WindowsArm32 = enum.auto()
    WindowsArm64 = enum.auto()
    Wasm32 = enum.auto()
    LinuxX86 = enum.auto()
    LinuxAmd64 = enum.auto()
    LinuxArm32 = enum.auto()
    LinuxArm64 = enum.auto()


class Platform(object, metaclass=abc.ABCMeta):
    name_map = {}
    
    def __init__(self, name: str, pointer_width_in_bits: int) -> None:
        super().__init__()
        assert name not in Platform.name_map
        Platform.name_map[name] = self

        self.name = name
        self.pointer_width_in_bits = pointer_width_in_bits


class CorePlatform(Platform):
    def __init__(self, core_platform_type: CorePlatformType, name: str, pointer_width_in_bits: int) -> None:
        super().__init__(name, pointer_width_in_bits)
        self.core_platform_type = core_platform_type


core_macos_amd64 = CorePlatform(CorePlatformType.MacOsAmd64, "macos-amd64", 64)
core_macos_arm64 = CorePlatform(CorePlatformType.MacOsArm64, "macos-arm64", 64)
core_windows_x86 = CorePlatform(CorePlatformType.WindowsX86, "windows-x86", 32)
core_windows_amd64 = CorePlatform(CorePlatformType.WindowsAmd64, "windows-amd64", 64)
core_windows_arm32 = CorePlatform(CorePlatformType.WindowsArm32, "windows-arm32", 32)
core_windows_arm64 = CorePlatform(CorePlatformType.WindowsArm64, "windows-arm64", 64)
core_wasm32 = CorePlatform(CorePlatformType.Wasm32, "wasm32", 32)
core_linux_x86 = CorePlatform(CorePlatformType.LinuxX86, "linux-x86", 32)
core_linux_amd64 = CorePlatform(CorePlatformType.LinuxAmd64, "linux-amd64", 64)
core_linux_arm32 = CorePlatform(CorePlatformType.LinuxArm32, "linux-arm32", 32)
core_linux_arm64 = CorePlatform(CorePlatformType.LinuxArm64, "linux-arm64", 64)
core_platform_list = [
    core_macos_amd64,
    core_macos_arm64,
    core_windows_x86,
    core_windows_amd64,
    core_windows_arm32,
    core_windows_arm64,
    core_wasm32,
    core_linux_x86,
    core_linux_amd64,
    core_linux_arm32,
    core_linux_arm64
]
core_platform_names = {core_platform.name for core_platform in core_platform_list}
