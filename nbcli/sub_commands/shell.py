from concurrent.futures import ThreadPoolExecutor
import pkgutil
import sys
import pynetbox
from pynetbox.core.endpoint import Endpoint
from .base import BaseSubCommand
from ..core import get_req
from ..views.tools import nbprint

class Shell():

    def __init__(self, netbox,
                 interactive_shell=None,
                 script=None,
                 interact=False,
                 skip_models=False):

        if pkgutil.find_loader('IPython') is None:
            interactive_shell = 'python'

        self.interactive_shell = interactive_shell
        self.script = script
        self.interact = interact
        self.netbox = netbox
        self.banner = ''
        self.banner += 'Python ' + sys.version.splitlines()[0] + '\n'
        self.banner += 'NetBox {} | pynetbox {}\n'.format(self.netbox.version, pynetbox.__version__)
        self.build_ns(skip_models=skip_models) 


    def build_ns(self, skip_models=False):

        self.ns = dict(Netbox=self.netbox)

        def load_models(item):
            app, url = item
            appobj = getattr(self.netbox, app)
            models = get_req(self.netbox, url)
            for model in models.keys():
                if model[0] != '_':
                    modelname = model.title().replace('-', '')
                    modelobj = getattr(appobj, model.replace('-', '_'))
                    if app == 'Virtualization' and model == "interfaces":
                        modelname = 'VirtualInterfaces'
                    self.ns[modelname] = modelobj

        if not skip_models:
            apps = get_req(self.netbox, self.netbox.base_url)

            if self.netbox.threading:
                with ThreadPoolExecutor() as executor:
                    executor.map(load_models, apps.items())
            else:
                for item in apps.items():
                    load_models(item)

            nbns = dict(self.ns)

            def lsmodels():

                modeldict = dict()

                for key, value in nbns.items():
                    if isinstance(value, Endpoint):
                        app = value.url.split('/')[-2].title()
                        if app in modeldict.keys():
                            modeldict[app].append(key)
                        else:
                            modeldict[app] = list()
                            modeldict[app].append(key)

                for app, modellist in sorted(modeldict.items()):
                    print(app + ':')
                    for model in sorted(modellist):
                        print('  ' + model)

            self.ns['lsmodels'] = lsmodels
            self.banner += 'lsmodels() will show available pynetbox models.\n'


        self.ns['nbprint'] = nbprint

    def python(self):
        from code import interact, InteractiveConsole
        banner = self.banner
        console = InteractiveConsole(locals=self.ns)
        if self.script:
            console.runcode(open(self.script).read())
            if self.interact:
                console.interact(banner='')
        else:
            console.interact(banner=banner)
    
    def ipython(self):
        from IPython import start_ipython
        from traitlets.config.loader import Config
    
        c = Config()
        c.TerminalInteractiveShell.banner1 = self.banner
        argv=[]

        if self.script:
            if self.interact:
                c.TerminalInteractiveShell.banner1 = ''
                argv.append('-i')
            argv.append(self.script)

        start_ipython(argv=argv, user_ns=self.ns, config=c)
    
    def run(self):
        if self.interactive_shell == 'ipython':
            self.ipython()
        else:
            self.python()


class ShellSubCommand(BaseSubCommand):
    """Launch Interactive Shell with pynetbox objects preloaded."""

    name = 'shell'
    parser_kwargs = dict(help='Launch interactive shell')

    def setup(self):

        self.parser.add_argument('script', nargs='?', type=str, help='Script to run')
        self.parser.add_argument('-i', action='store_true',
                      help='inspect interactively after running script')
        self.parser.add_argument('-s', '--interactive-shell', choices=['python', 'ipython'],
                      default='ipython',
                      help='Specifies interactive shell to use')
        self.parser.add_argument('--skip',
                                 action='store_true',
                                 help='Skip loading models.')

    def run(self):
        """Run Shell enviornment.

        Example usage:
        $ nbcli shell -i myscript.py
        $ nbcli shell -s python"""
 
        shell = Shell(self.netbox,
                      interactive_shell=self.args.interactive_shell,
                      script=self.args.script,
                      interact=self.args.i,
                      skip_models=self.args.skip)
        shell.run()
