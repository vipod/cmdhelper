"""cmdhelper.errors

Provides exceptions used by the cmdhelper modules.

This module is safe to use in "from ... import *" mode; it only exports
symbols whose names start with "CMDHelper" and end with "Error"."""


class CMDHelperError(Exception):
    """The root of all CMDHelper errors."""
    pass

class CMDHelperModuleError(CMDHelperError):
    """Unable to load an expected module, or to find an expected class
    within some module (in particular, command modules and classes)."""
    pass

class CMDHelperClassError(CMDHelperError):
    """Some command class or inherited from CMDHelper class is found not
    to be holding up its end of the bargain, ie. implementing some part
    of the "command "interface."""
    pass

class CMDHelperGetoptError(CMDHelperError):
    """The option table provided to 'fancy_getopt()' is bogus."""
    pass

class CMDHelperArgError(CMDHelperError):
    """Raised by fancy_getopt in response to getopt.error -- ie. an
    error in the command line usage."""
    pass

class CMDHelperFileError(CMDHelperError):
    """Any problems in the filesystem: expected file not found, etc.
    Typically this is for problems that we detect before IOError or
    OSError could be raised."""
    pass

class CMDHelperOptionError(CMDHelperError):
    """Syntactic/semantic errors in command options, such as use of
    mutually conflicting options, or inconsistent options,
    badly-spelled values, etc."""
    pass

class CMDHelperPlatformError(CMDHelperError):
    """We don't know how to do something on the current platform (but
    we do know how to do it on some platform)."""
    pass

class CMDHelperExecError(CMDHelperError):
    """Any problems executing an external program (such as the C
    compiler, when compiling C files)."""
    pass

class CMDHelperInternalError(CMDHelperError):
    """Internal inconsistencies or impossibilities (obviously, this
    should never be seen if the code is working!)."""
    pass

class CMDHelperTemplateError(CMDHelperError):
    """Syntax error in a file list template."""

