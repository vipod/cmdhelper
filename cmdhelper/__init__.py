"""cmdhelper

This is the main cmdhelper class which represents command line utility
base class. It can be used as base class for any specific command line
utility or as it is as well.

This class is simply a copy of distutils.dist.Distribution class but with
stripped down all distribution related stuff. CMDHelper contains only those
things required for command line utilities.
"""

import sys, os, string, re
from types import *
from copy import copy

try:
    import warnings
except ImportError:
    warnings = None

from distutils.fancy_getopt import FancyGetopt, translate_longopt
from distutils.util import check_environ, strtobool
from distutils import log
from distutils.dist import fix_help_options, command_re
import pkg_resources

from cmdhelper.debug import DEBUG
from cmdhelper.errors import *


class CMDHelper(object):
    """The core of the cmdhelper package. 
    
    If you know how to write distutils/setuptools commands then you
    already know how to write command line utilities using this package.
    This is because cmdhelper package is stripped down version of distutils
    Distribution && Command classes. All Distribution related stuff was 
    removed and only command-line goodness including parsing configuration
    files, command lines, running commands, etc... was taken from distutils.
    """


    # 'global_options' describes the command-line options that may be
    # supplied to the CMDHelper init prior to any actual commands.
    # Eg. "some_utility.py -n" or "some_utility.py --quiet" both take advantage
    # of these global options. This list should be kept to a bare minimum,
    # since every global option is also valid as a command option -- and we
    # don't want to pollute the commands with too many options that they
    # have minimal control over.
    # The fourth entry for verbose means that it can be repeated.
    global_options = [('verbose', 'v', "run verbosely (default)", 1),
                      ('quiet', 'q', "run quietly (turns verbosity off)"),
                      ('dry-run', 'n', "don't actually do anything"),
                      ('help', 'h', "show detailed help message"),
                     ]

    # options that are global utility options but are not propagated to
    # utility commands, not sure yet whether this kind of options is really
    # useful
    cmdhelper_only_options = [
        ('config-file=', 'c', "path to configuration file (not working yet)")
    ]
    
    # list of required options
    required_options = []

    # options that are not propagated to the commands
    display_options = [
        ('help-commands', None, "list all available commands"),
    ]

    display_option_names = map(lambda x: translate_longopt(x[0]),
                               display_options)

    # negative options are options that exclude other options
    negative_opt = {'quiet': 'verbose'}

    def __init__(self, entry_point, attrs=None):
        """Construct a new CMDHelper instance: initialize all the
        attributes of a command-line utility, and then use 'attrs' (a
        dictionary mapping attribute names to values) to assign some of those
        attributes their "real" values.  (Any attributes not mentioned in
        'attrs' will be assigned to some null value: 0, None, an empty list
        or dictionary, etc.)  Most importantly, initialize the
        'command_obj' attribute to the empty dictionary; this will be
        filled in with real command objects by 'parse_command_line()'.
        """

        # Entry point name which cmdhelper will collect commands from
        self.entry_point = entry_point

        # Path to configuration file
        self.config_file = ''
        
        # Default values for our command-line options
        self.verbose = 1
        self.dry_run = 0
        self.help = 0
        for attr in self.display_option_names:
            setattr(self, attr, 0)

        # 'cmdclass' maps command names to class objects, so we
        # can 1) quickly figure out which class to instantiate when
        # we need to create a new command object, and 2) have a way
        # for the command line utilities to override command classes
        self.cmdclass = {}

        self.script_name = os.path.basename(sys.argv[0])
        self.script_args = sys.argv[1:]

        # 'command_options' is where we store command options between
        # parsing them (from config files, the command-line, etc.) and when
        # they are actually needed -- ie. when the command in question is
        # instantiated.  It is a dictionary of dictionaries of 2-tuples:
        #   command_options = { command_name : { option : (source, value) } }
        self.command_options = {}

        # And now initialize bookkeeping stuff that can't be supplied by
        # the caller at all.  'command_obj' maps command names to
        # Command instances -- that's how we enforce that every command
        # class is a singleton.
        self.command_obj = {}

        # 'have_run' maps command names to boolean values; it keeps track
        # of whether we have actually run a particular command, to make it
        # cheap to "run" a command whenever we think we might need to -- if
        # it's already been done, no need for expensive filesystem
        # operations, we just check the 'have_run' dictionary and carry on.
        # It's only safe to query 'have_run' for a command class that has
        # been instantiated -- a false value will be inserted when the
        # command object is created, and replaced with a true value when
        # the command is successfully run.  Thus it's probably best to use
        # '.get()' rather than a straight lookup.
        self.have_run = {}

        # Now we'll use the attrs dictionary (ultimately, keyword args from
        # the setup script) to possibly override any or all of these
        # CMDHelper options.

        if attrs:

            # Pull out the set of command options and work on them
            # specifically.  Note that this order guarantees that aliased
            # command options will override any supplied redundantly
            # through the general options dictionary.
            options = attrs.get('options')
            if options:
                del attrs['options']
                for (command, cmd_options) in options.items():
                    opt_dict = self.get_option_dict(command)
                    for (opt, val) in cmd_options.items():
                        opt_dict[opt] = ("utility script", val)

            # Now work on the rest of the attributes.  Any attribute that's
            # not already defined is invalid!
            for (key,val) in attrs.items():
                if hasattr(self, key):
                    setattr(self, key, val)
                else:
                    msg = "Unknown cmdhelper option: %s" % repr(key)
                    if warnings is not None:
                        warnings.warn(msg)
                    else:
                        sys.stderr.write(msg + "\n")

    def get_option_dict(self, command):
        """Get the option dictionary for a given command.  If that
        command's option dictionary hasn't been created yet, then create it
        and return the new dictionary; otherwise, return the existing
        option dictionary.
        """

        dict = self.command_options.get(command)
        if dict is None:
            dict = self.command_options[command] = {}
        return dict


    def dump_option_dicts(self, header=None, commands=None, indent=""):
        from pprint import pformat

        if commands is None:             # dump all command option dicts
            commands = self.command_options.keys()
            commands.sort()

        if header is not None:
            print indent + header
            indent = indent + "  "

        if not commands:
            print indent + "no commands known yet"
            return

        for cmd_name in commands:
            opt_dict = self.command_options.get(cmd_name)
            if opt_dict is None:
                print indent + "no option dict for '%s' command" % cmd_name
            else:
                print indent + "option dict for '%s' command:" % cmd_name
                out = pformat(opt_dict)
                for line in string.split(out, "\n"):
                    print indent + "  " + line

    def find_config_files(self):
        """Find as many configuration files as should be processed for this
        platform, and return a list of filenames in the order in which they
        should be parsed.  The filenames returned are guaranteed to exist
        (modulo nasty race conditions).

        Look for configuration file in the user's home directory named
        .karm.cfg on Unix and karm.cfg on Windows/Mac.
        """
        files = []
        if self.config_file:
            files.append(self.config_file)
        check_environ()

        # What to call the per-user config file
        if os.name == 'posix':
            user_filename = ".karm.cfg"
        else:
            user_filename = "karm.cfg"

        # And look for the user config file
        if os.environ.has_key('HOME'):
            user_file = os.path.join(os.environ.get('HOME'), user_filename)
            if os.path.isfile(user_file):
                files.append(user_file)

        return files

    def parse_config_files(self, filenames=None):

        from ConfigParser import ConfigParser

        if filenames is None:
            filenames = self.find_config_files()

        if DEBUG: print "CMDHelper.parse_config_files():"

        parser = ConfigParser()
        for filename in filenames:
            if DEBUG: print "  reading", filename
            parser.read(filename)
            for section in parser.sections():
                options = parser.options(section)
                opt_dict = self.get_option_dict(section)

                for opt in options:
                    if opt != '__name__':
                        val = parser.get(section, opt)
                        opt = string.replace(opt, '-', '_')
                        opt_dict[opt] = (filename, val)

            # Make the ConfigParser forget everything (so we retain
            # the original filenames that options come from)
            parser.__init__()

        # If there was a "global" section in the config file, use it
        # to set CMDHelper options.
        if self.command_options.has_key('global'):
            for (opt, (src, val)) in self.command_options['global'].items():
                alias = self.negative_opt.get(opt)
                try:
                    if alias:
                        setattr(self, alias, not strtobool(val))
                    elif opt in ('verbose', 'dry_run'): # ugh!
                        setattr(self, opt, strtobool(val))
                    else:
                        setattr(self, opt, val)
                except ValueError, msg:
                    raise CMDHelperOptionError, msg

    def parse_command_line(self):
        """Parse the utility's command line, taken from the
        'script_args' instance attribute (which defaults to 'sys.argv[1:]'.
        This list is first processed for "global options" -- options that
        set attributes of the CMDHelper instance.  Then, it is alternately
        scanned for command line commands and options for that command.
        Each new command terminates the options for the previous command.
        The allowed options for a command are determined by the 'user_options'
        attribute of the command class -- thus, we have to be able to load
        command classes in order to parse the command line.  Any error in that
        'options' attribute raises CMDHelperGetoptError; any error on the
        command-line raises CMDHelperArgError.  If no cmdhelper commands
        were found on the command line, raises CMDHelperArgError.  Return
        true if command-line was successfully parsed and we should carry
        on with executing commands; false if no errors but we shouldn't
        execute commands (currently, this only happens if user asks for
        help).
        """
        toplevel_options = self._get_toplevel_options()

        # We have to parse the command line a bit at a time -- global
        # options, then the first command, then its options, and so on --
        # because each command will be handled by a different class, and
        # the options that are valid for a particular class aren't known
        # until we have loaded the command class, which doesn't happen
        # until we know what the command is.

        self.commands = []
        parser = FancyGetopt(toplevel_options + self.display_options)
        parser.set_negative_aliases(self.negative_opt)
        args = parser.getopt(args=self.script_args, object=self)
        option_order = parser.get_option_order()
        log.set_verbosity(self.verbose)

        # for display options we return immediately
        if self.handle_display_options(option_order):
            return

        while args:
            args = self._parse_command_opts(parser, args)
            if args is None:            # user asked for help (and got it)
                return

        # Handle the cases of --help as a "global" option, ie.
        # "some_utility.py --help" and "some_utility.py --help command ...".
        # For the former, we show global options (--verbose, --dry-run, etc.)
        # and display-only options (--help-commands, etc.); for the
        # latter, we omit the display-only options and show help for
        # each command listed on the command line.
        if self.help or not self.commands:
            self._show_help(parser,
                            display_options=len(self.commands) == 0,
                            commands=self.commands)
            return

        # All is well: return true
        return 1

    def _get_toplevel_options(self):
        """Return the non-display options recognized at the top level.

        This includes options that are recognized *only* at the top
        level as well as options recognized for commands.
        """
        return self.global_options + self.cmdhelper_only_options

    def _parse_command_opts(self, parser, args):
        """Parse the command-line options for a single command.
        'parser' must be a FancyGetopt instance; 'args' must be the list
        of arguments, starting with the current command (whose options
        we are about to parse).  Returns a new version of 'args' with
        the next command at the front of the list; will be the empty
        list if there are no more commands on the command line.  Returns
        None if the user asked for help on this command.
        """
        # late import because of mutual dependence between these modules
        from cmdhelper.cmd import Command

        # Pull the current command from the head of the command line
        command = args[0]
        if not command_re.match(command):
            raise SystemExit, "invalid command name '%s'" % command
        self.commands.append(command)

        # Dig up the command class that implements this command, so we
        # 1) know that it's a valid command, and 2) know which options
        # it takes.
        try:
            cmd_class = self.get_command_class(command)
        except CMDHelperModuleError, msg:
            raise CMDHelperArgError, msg

        # Require that the command class be derived from Command -- want
        # to be sure that the basic "command" interface is implemented.
        if not issubclass(cmd_class, Command):
            raise CMDHelpersClassError, \
                  "command class %s must subclass Command" % cmd_class

        # Also make sure that the command object provides a list of its
        # known options.
        if not (hasattr(cmd_class, 'user_options') and
                type(cmd_class.user_options) is ListType):
            raise CMDHelperClassError, \
                  ("command class %s must provide " +
                   "'user_options' attribute (a list of tuples)") % \
                  cmd_class

        # If the command class has a list of negative alias options,
        # merge it in with the global negative aliases.
        negative_opt = self.negative_opt
        if hasattr(cmd_class, 'negative_opt'):
            negative_opt = copy(negative_opt)
            negative_opt.update(cmd_class.negative_opt)

        # Check for help_options in command class.  They have a different
        # format (tuple of four) so we need to preprocess them here.
        if (hasattr(cmd_class, 'help_options') and
            type(cmd_class.help_options) is ListType):
            help_options = fix_help_options(cmd_class.help_options)
        else:
            help_options = []


        # All commands support the global options too, just by adding
        # in 'global_options'.
        parser.set_option_table(self.global_options +
                                cmd_class.user_options +
                                help_options)
        parser.set_negative_aliases(negative_opt)
        (args, opts) = parser.getopt(args[1:])
        if hasattr(opts, 'help') and opts.help:
            self._show_help(parser, display_options=0, commands=[cmd_class])
            return

        if (hasattr(cmd_class, 'help_options') and
            type(cmd_class.help_options) is ListType):
            help_option_found = 0
            for (help_option, short, desc, func) in cmd_class.help_options:
                if hasattr(opts, parser.get_attr_name(help_option)):
                    help_option_found=1
                    if callable(func):
                        func()
                    else:
                        raise CMDHelperClassError(
                            "invalid help function %r for help option '%s': "
                            "must be a callable object (function, etc.)"
                            % (func, help_option))

            if help_option_found:
                return

        # Put the options from the command-line into their official
        # holding pen, the 'command_options' dictionary.
        opt_dict = self.get_option_dict(command)
        for (name, value) in vars(opts).items():
            opt_dict[name] = ("command line", value)

        return args

    def _show_help(self,
                   parser,
                   global_options=1,
                   display_options=1,
                   commands=[]):
        """Show help for the command line utility in the form of
        several lists of command-line options. 'parser' should be a
        FancyGetopt instance; do not expect it to be returned in the
        same state, as its option table will be reset to make it
        generate the correct help text.

        If 'global_options' is true, lists the global options:
        --verbose, --dry-run, etc.  If 'display_options' is true, lists
        the "display-only" options: --help-commands, etc. Finally,
        lists per-command help for every command name or command class
        in 'commands'.
        """
        from distutils.core import gen_usage
        from cmdhelper.cmd import Command

        if global_options:
            if display_options:
                options = self._get_toplevel_options()
            else:
                options = self.global_options
            parser.set_option_table(options)
            parser.print_help("Global options:")
            print

        if display_options:
            parser.set_option_table(self.display_options)
            parser.print_help(
                "Information display options (just display " +
                "information, ignore any commands)")
            print

        for command in self.commands:
            if type(command) is ClassType and issubclass(command, Command):
                klass = command
            else:
                klass = self.get_command_class(command)
            if (hasattr(klass, 'help_options') and
                type(klass.help_options) is ListType):
                parser.set_option_table(klass.user_options +
                                        fix_help_options(klass.help_options))
            else:
                parser.set_option_table(klass.user_options)
            parser.print_help("Options for '%s' command:" % klass.__name__)
            print

        print gen_usage(self.script_name)
        return

    def handle_display_options(self, option_order):
        """If there were any non-global "display-only" options
        (--help-commands) on the command line, display the requested
        info and return true; else return false.
        """
        from distutils.core import gen_usage

        # User just wants a list of commands -- we'll print it out and stop
        # processing now (ie. if they ran
        #    "some_utility.py --help-commands foo bar",
        # we ignore "foo bar").
        if self.help_commands:
            self.print_commands()
            print
            print gen_usage(self.script_name)
            return 1

        return 0

    def print_command_list(self, commands, header, max_length):
        """Print a subset of the list of all commands -- used by
        'print_commands()'.
        """

        print header + ":"

        for cmd in commands:
            klass = self.cmdclass.get(cmd)
            if not klass:
                klass = self.get_command_class(cmd)
            try:
                description = klass.description
            except AttributeError:
                description = "(no description available)"

            print "  %-*s  %s" % (max_length, cmd, description)

    def print_commands(self):
        """Print out a help message listing all available commands with a
        description of each.  The list is divided into "standard commands"
        (listed in cmdhelper.command.__all__) and "extra commands"
        (mentioned in self.cmdclass, but not a standard command).  The
        descriptions come from the command class attribute
        'description'.
        """
        for ep in pkg_resources.iter_entry_points(self.entry_point):
            if ep.name not in self.cmdclass:
                cmdclass = ep.load(False) # don't require extras, we're not running
                self.cmdclass[ep.name] = cmdclass

        commands = []
        for cmd in self.cmdclass.keys():
            commands.append(cmd)

        max_length = 0
        for cmd in commands:
            if len(cmd) > max_length:
                max_length = len(cmd)

        self.print_command_list(commands, "Commands", max_length)

    def get_command_class(self, command):
        """Pluggable version of get_command_class()"""
        if command in self.cmdclass:
            return self.cmdclass[command]

        from setuptools.dist import Distribution
        dist = Distribution()
        for ep in pkg_resources.iter_entry_points(self.entry_point, command):
            ep.require(installer=dist.fetch_build_egg)
            self.cmdclass[command] = cmdclass = ep.load()
            return cmdclass
        
        raise CMDHelperModuleError("invalid command '%s'" % command)

    def get_command_obj(self, command, create=1):
        """Return the command object for 'command'.  Normally this object
        is cached on a previous call to 'get_command_obj()'; if no command
        object for 'command' is in the cache, then we either create and
        return it (if 'create' is true) or return None.
        """
        cmd_obj = self.command_obj.get(command)
        if not cmd_obj and create:
            if DEBUG:
                print "cmdhelper.get_command_obj(): " \
                      "creating '%s' command object" % command

            klass = self.get_command_class(command)
            cmd_obj = self.command_obj[command] = klass(self)
            self.have_run[command] = 0

            # Set any options that were supplied in config files
            # or on the command line.  (NB. support for error
            # reporting is lame here: any errors aren't reported
            # until 'finalize_options()' is called, which means
            # we won't report the source of the error.)
            options = self.command_options.get(command)
            if options:
                self._set_command_options(cmd_obj, options)

        return cmd_obj

    def _set_command_options(self, command_obj, option_dict=None):
        """Set the options for 'command_obj' from 'option_dict'.  Basically
        this means copying elements of a dictionary ('option_dict') to
        attributes of an instance ('command').

        'command_obj' must be a Command instance.  If 'option_dict' is not
        supplied, uses the standard option dictionary for this command
        (from 'self.command_options').
        """
        command_name = command_obj.get_command_name()
        if option_dict is None:
            option_dict = self.get_option_dict(command_name)

        if DEBUG: print "  setting options for '%s' command:" % command_name
        for (option, (source, value)) in option_dict.items():
            if DEBUG: print "    %s = %s (from %s)" % (option, value, source)
            try:
                bool_opts = map(translate_longopt, command_obj.boolean_options)
            except AttributeError:
                bool_opts = []
            try:
                neg_opt = command_obj.negative_opt
            except AttributeError:
                neg_opt = {}

            try:
                is_string = type(value) is StringType
                if neg_opt.has_key(option) and is_string:
                    setattr(command_obj, neg_opt[option], not strtobool(value))
                elif option in bool_opts and is_string:
                    setattr(command_obj, option, strtobool(value))
                elif hasattr(command_obj, option):
                    setattr(command_obj, option, value)
                else:
                    raise CMDHelperOptionError, \
                          ("error in %s: command '%s' has no such option '%s'"
                           % (source, command_name, option))
            except ValueError, msg:
                raise CMDHelperOptionError, msg

    def reinitialize_command(self, command, reinit_subcommands=0):
        """Reinitializes a command to the state it was in when first
        returned by 'get_command_obj()': ie., initialized but not yet
        finalized.  This provides the opportunity to sneak option
        values in programmatically, overriding or supplementing
        user-supplied values from the config files and command line.
        You'll have to re-finalize the command object (by calling
        'finalize_options()' or 'ensure_finalized()') before using it for
        real.

        'command' should be a command name (string) or command object.  If
        'reinit_subcommands' is true, also reinitializes the command's
        sub-commands, as declared by the 'sub_commands' class attribute (if
        it has one).  See the "install" command for an example.  Only
        reinitializes the sub-commands that actually matter, ie. those
        whose test predicates return true.

        Returns the reinitialized command object.
        """
        from cmdhelper.cmd import Command
        if not isinstance(command, Command):
            command_name = command
            command = self.get_command_obj(command_name)
        else:
            command_name = command.get_command_name()

        if not command.finalized:
            return command
        command.initialize_options()
        command.finalized = 0
        self.have_run[command_name] = 0
        self._set_command_options(command)

        if reinit_subcommands:
            for sub in command.get_sub_commands():
                self.reinitialize_command(sub, reinit_subcommands)

        return command

    def announce(self, msg, level=1):
        log.debug(msg)

    def checkRequiredOptions(self):
        for option in self.required_options:
            if not getattr(self, option, False):
                raise CMDHelperOptionError, '%s option is required' % option

    def run(self):
        """Join all the goodness incorporated in this class"""
        
        # Find and parse the config file(s): they will override options from
        # the init, but be overridden by the command line.
        self.parse_config_files()

        if DEBUG:
            print "options (after parsing config files):"
            self.dump_option_dicts()

        # Parse the command line; any command-line errors are the end user's
        # fault, so turn them into SystemExit to suppress tracebacks.
        ok = self.parse_command_line()

        if DEBUG:
            print "options (after parsing command line):"
            self.dump_option_dicts()

        # And finally, run all the commands found on the command line.
        if ok:
            # check for required options, if there are missing
            # required options error will be raised
            self.checkRequiredOptions()
            self.run_commands()

        return self

    def run_commands(self):
        """Run each command that was seen on the utility command line.
        Uses the list of commands found and cache of command objects
        created by 'get_command_obj()'.
        """
        for cmd in self.commands:
            self.run_command(cmd)

    def run_command(self, command):
        """Do whatever it takes to run a command (including nothing at all,
        if the command has already been run).  Specifically: if we have
        already created and run the command named by 'command', return
        silently without doing anything.  If the command named by 'command'
        doesn't even have a command object yet, create one.  Then invoke
        'run()' on that command object (or an existing one).
        """
        # Already been here, done that? then return silently.
        if self.have_run.get(command):
            return

        log.info("running %s", command)
        cmd_obj = self.get_command_obj(command)
        cmd_obj.ensure_finalized()
        cmd_obj.run()
        self.have_run[command] = 1

if __name__ == "__main__":
    cmdhelper = CMDHelper()
    cmdhelper.run()
    print "ok"
