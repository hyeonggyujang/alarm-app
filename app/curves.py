import math


MAX_VOLUME = 0.8
MIN_VOLUME = 0.1
RAMP_SECONDS = 30 * 60  # 30 minutes


def get_volume(elapsed_seconds: float, curve: str) -> float:
    """
    Returns a volume between 0.0 and MAX_VOLUME (0.8)
    given how many seconds have elapsed since the ramp started.

    elapsed_seconds: seconds since audio began (0 → RAMP_SECONDS)
    curve:           'linear' | 'logarithmic' | 'exponential'
    """
    t = max(0.0, min(elapsed_seconds, RAMP_SECONDS))
    progress = t / RAMP_SECONDS  # 0.0 → 1.0

    if curve == "linear":
        scaled = progress

    elif curve == "logarithmic":
        # Rises quickly at first, then flattens — gentler finish
        scaled = math.log1p(progress * (math.e - 1))

    elif curve == "exponential":
        # Stays quiet longer, then rises sharply near wake time
        scaled = (math.exp(progress) - 1) / (math.e - 1)

    else:
        scaled = progress  # fallback to linear

    return round(MIN_VOLUME + scaled * (MAX_VOLUME - MIN_VOLUME), 4)