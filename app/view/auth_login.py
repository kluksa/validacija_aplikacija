# -*- coding: utf-8 -*-
from PyQt4 import uic

BASE_LOGIN_AUTH, FORM_LOGIN_AUTH = uic.loadUiType('./app/view/ui_files/auth_login.ui')
class DijalogLoginAuth(BASE_LOGIN_AUTH, FORM_LOGIN_AUTH):
    """Dijalog za login, unos username i passworda"""
    def __init__(self, parent=None):
        super(BASE_LOGIN_AUTH, self).__init__(parent)
        self.setupUi(self)
        self.u = None
        self.p = None
        self.LEUser.textEdited.connect(self.set_user)
        self.LEPass.textEdited.connect(self.set_pswd)

    def set_user(self, x):
        """setter za username"""
        self.u = str(x)

    def set_pswd(self, x):
        """setter za password"""
        self.p = str(x)

    def get_credentials(self):
        """getter za uneseni username i password"""
        return self.u, self.p