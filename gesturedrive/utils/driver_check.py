import winreg


def is_vigem_installed():
    """
    Returns True if ViGEm Bus Driver is installed.
    """

    try:
        winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\ViGEmBus"
        )
        return True

    except FileNotFoundError:
        return False

    except Exception:
        return False