import matplotlib as mpl

# Make *absolutely sure* we never try to invoke TeX during draw or savefig,
# which would hang under test timeouts.
mpl.rcParams["text.usetex"] = False

__all__ = []
