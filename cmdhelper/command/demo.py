"""cmdhelper.command.demo

Demonsrate usage of cmdhelper package.
This Demo command is registered as cmdhelper.demo entry point.
"""

from cmdhelper.cmd import Command
from cmdhelper.errors import *

class Demo(Command):

    description = 'Demonstrates how to use cmdhelper package, ' \
                  'this command can only print messages'

    user_options = [
        ('message=', 'm', 'message to be printed'),
        ('prefix=', 'p', 'prefix before printed message'),
        ('sufix=', 's', 'sufix after printed message'),
        ('uppercase', 'u', 'print capitalized messages'),
        ('lowercase', 'l', 'print messages in lower case'),
        ('capitalize', None, 'capitalize printed message'),
    ]

    boolean_options = [
        'uppercase', 'lowercase', 'capitalize',
    ]

    negative_options = {}

    help_options = []

    def initialize_options(self):
        self.message = ''
        self.prefix = ''
        self.sufix = ''
        self.uppercase = 0
        self.lowercase = 0
        self.capitalize = 0

    def finalize_options(self):
        # define priorities
        if self.lowercase:
            self.uppercase = 0
        if self.capitalize:
            self.lowercase = 0
            self.uppercase = 0
            
    def run(self):
        if not self.message:
            raise CMDHelperArgError, '--message (-m) is required option'
        
        msg = self.message[:]
        if self.capitalize:
            msg = msg.capitalize()
        elif self.lowercase:
            msg = msg.lower()
        elif self.uppercase:
            msg = msg.upper()
            
        print '%s%s%s' % (self.prefix, msg, self.sufix)
        return self

def main():
    from cmdhelper import CMDHelper
    app = CMDHelper(entry_point='cmdhelper.demo')
    app.run()
    
if __name__ == '__main__':
    main()
