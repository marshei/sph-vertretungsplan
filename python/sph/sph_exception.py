""" SPH exception """


class SphException(Exception):
    """Indicating an exception related to the SPH checks"""


class SphLoggedOutException(Exception):
    """Indicating that the session has been logged out from the SPH"""
