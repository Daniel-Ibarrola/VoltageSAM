import os


def get_env_var(var_name: str, default: str = "") -> str:
    env = os.environ.get(var_name, default)
    if not env:
        raise ValueError(f"Need to define {var_name} env variable.")
    return env
