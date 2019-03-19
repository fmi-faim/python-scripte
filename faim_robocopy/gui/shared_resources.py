from tkinter import StringVar
from tkinter import DoubleVar
from tkinter import IntVar


class SharedResources:
    '''manages shared variables.

    '''

    def __init__(self, source, dest1, dest2, user_mail):
        '''
        '''
        self.source_var = StringVar()
        self.source_var.set(source)

        self.dest1_var = StringVar()
        self.dest1_var.set(dest1)

        self.dest2_var = StringVar()
        self.dest2_var.set(dest2)

        self.secure_mode_var = IntVar()
        self.secure_mode_var.set(1)

        self.multithreaded_var = IntVar()
        self.multithreaded_var.set(0)

        self.silent_var = IntVar()
        self.silent_var.set(0)

        self.delete_src_var = IntVar()
        self.delete_src_var.set(0)

        self.omit_files_var = StringVar()
        self.omit_files_var.set('')

        self.time_interval_var = DoubleVar()
        self.time_interval_var.set(0.5)

        self.time_exit_var = DoubleVar()
        self.time_exit_var.set(5)

        self.mail_var = StringVar()
        self.mail_var.set(user_mail)

    def update_from_settings(self, settings):
        '''
        '''
        section = 'default_params'
        for key, variable in zip([
                'secure_mode', 'multithreaded', 'silent', 'delete_src',
                'time_to_exit_in_s', 'time_interval_in_s'
        ], [
                self.secure_mode_var, self.multithreaded_var, self.silent_var,
                self.delete_src_var, self.time_exit_var, self.time_interval_var
        ]):

            if settings[section].get(key, None) is None:
                continue

            if key.endswith('_in_s'):
                val = settings[section].getfloat(
                    key) / 60.  # conversion to min.
            else:
                val = settings[section].getboolean(key)

            variable.set(val)
