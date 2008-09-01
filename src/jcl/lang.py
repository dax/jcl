# -*- coding: utf-8 -*-
##
## lang.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Sat Jan 28 16:37:11 2006 David Rousselie
## $Id$
##
## Copyright (C) 2006 David Rousselie
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##

"""
lang -- contains translations
"""

__revision__ = "$Id: lang.py,v 1.3 2005/09/18 20:24:07 dax Exp $"

class Lang:
    """
    Lang.
    """

    # pylint: disable-msg=W0232, R0903, C0103, C0111
    def __init__(self, default_lang = "en"):
        self.default_lang = default_lang

    def get_lang_from_node(self, node):
        """
        Extract lang contain in a XML node.

        :Parameters:
           - `node`: XML node.
        """
        lang = node.getLang()
        if lang is None:
            lang = self.default_lang
        return lang

    def get_lang_class(self, lang):
        """Return lang class from lang code.

        :Parameters:
           - `lang`: lang code.
        """
        if lang is not None:
            lang = lang[:2]
        if hasattr(self.__class__, lang):
            return getattr(self.__class__, lang)
        return getattr(self.__class__, self.default_lang)

    def get_lang_class_from_node(self, node):
        """Return lang class from XML node.

        :Parameters:
           - `node`: XML node.
        """
        return self.get_lang_class(self.get_lang_from_node(node))

    def get_default_lang_class(self):
        """Return default lang class according to self.default_lang"""
        return self.get_lang_class(self.default_lang)

    class en(object):
        component_name = u"Jabber Component Library generic component"
        register_title = u"Create new account"
        register_instructions = u"Enter account parameters"
        message_status = u" accounts registered."
        account_name = u"Account name"

        password_saved_for_session = u"Password will be kept during your " \
                                     u"Jabber session"
        ask_password_subject = u"Password request"
        ask_password_body = u"Reply to this message with the password " \
                            "for account %s\n"
        new_account_message_subject = u"New account '%s' created"
        new_account_message_body = u"New account created"
        update_account_message_subject = u"Updated account '%s'"
        update_account_message_body = u"Updated account"

        field_error = u"Error with '%s' field: %s"
        mandatory_field = u"required field"
        not_well_formed_field = u"not well formed field"

        field_chat_action = u"Action when state is 'Free For Chat'"
        field_online_action = u"Action when state is 'Online'"
        field_away_action = u"Action when state is 'Away'"
        field_xa_action = u"Action when state is 'Not Available'"
        field_dnd_action = u"Action when state is 'Do not Disturb'"
        field_offline_action = u"Action when state is 'Offline'"

        field_action_0 = u"Do nothing"
        field_chat_action_0 = field_action_0
        field_online_action_0 = field_action_0
        field_away_action_0 = field_action_0
        field_xa_action_0 = field_action_0
        field_dnd_action_0 = field_action_0
        field_offline_action_0 = field_action_0

        field_user_jid = u"User Jabber ID"
        field_password = u"Password"

        error_subject = u"Error"
        error_body = u"An error has occured:\n\t%s"

        get_gateway_desc = u"Please enter the email address of your contact"
        get_gateway_prompt = u"Email address"

        command_add_user = u"Create new account"
        command_add_user_1_description = u"Select an account type"
        field_account_type = u"Account type"

        command_delete_user = u"Delete accounts"
        command_delete_user_1_description = \
            u"Fill out this form with user(s) Jabber ID(s) to search account(s) to delete"
        command_delete_user_2_description = u"Select account(s) to delete"
        field_users_jids = u"User(s) Jabber ID(s)"
        field_account = u"Account"
        field_accounts = u"Accounts"

        command_disable_user = u"Disable accounts"
        command_disable_user_1_description = \
            u"Fill out this form with user(s) Jabber ID(s) to search account(s) to disable"
        command_disable_user_2_description = u"Select account(s) to disable"

        command_reenable_user = u"Re-Enable accounts"
        command_reenable_user_1_description = \
            u"Fill out this form with user(s) Jabber ID(s) to search account(s) to re-enable"
        command_reenable_user_2_description = u"Select account(s) to re-enable"

        command_end_user_session = u"End users sessions"
        command_end_user_session_1_description = \
            u"Fill out this form with user(s) Jabber ID(s) to search account(s) to end session"
        command_end_user_session_2_description = \
            u"Select account(s) to end their session"

        command_get_user_password = u"Get user&apos;s password"
        command_get_user_password_1_description = \
            u"Fill out this form with user Jabber ID to search account" \
            u" for which to retrieve password"
        command_get_user_password_2_description = \
            u"Select account for which to retrieve password"

        command_change_user_password = u"Changing user&apos;s password"
        command_change_user_password_1_description = \
            u"Fill out this form with user Jabber ID to search account" \
            u" for which to change password"
        command_change_user_password_2_description = \
            u"Select account for which to change password"

        command_get_user_roster = u"Get user's accounts"
        command_get_user_roster_1_description = \
            u"Fill out this form with user Jabber ID for which to retrieve accounts"

        command_get_user_lastlogin = u"Get user's last login time"
        command_get_user_lastlogin_1_description = \
            u"Fill out this form with user Jabber ID to search account" \
            u" for which to retrieve last login time"
        command_get_user_lastlogin_2_description = \
            u"Select account for which to retrieve last login time"

        command_get_registered_users_num = u"Get the number of " \
                                           u"registered accounts"
        command_get_disabled_users_num = u"Get the number of disabled accounts"
        command_get_online_users_num = u"Get the number of online accounts"

        command_get_registered_users_list = u"Get the list of " \
                                           u"registered accounts"
        command_get_disabled_users_list = u"Get the list of disabled accounts"
        command_get_online_users_list = u"Get the list of online accounts"

        field_registered_users_num = u"The number of registered accounts"
        field_disabled_users_num = u"The number of disabled accounts"
        field_online_users_num = u"The number of online accounts"

        field_max_items = u"Maximum number of items to show"
        field_registered_users_list = u"The list of registered accounts"
        field_disabled_users_list = u"The list of disabled accounts"
        field_online_users_list = u"The list of online accounts"

        command_announce = u"Make an annoucement"
        command_announce_1_description = \
            u"Fill out this form with the announce to send to online users"
        field_announcement = u"Announcement"

        command_set_motd = u"Set the Message Of The Day"
        command_set_motd_1_description = \
            u"Fill out this form with the Message Of The Day to send to all" \
            u" registered users"
        field_motd = u"Message Of The Day"

        command_edit_motd = u"Edit the Message Of The Day"

        command_delete_motd = u"Delete the Message Of The Day"

        command_set_welcome = u"Set Welcome Message"
        command_set_welcome_1_description = \
            u"Fill out this form with the Welcome Message to send to all" \
            u" new registered users"
        field_welcome = u"Welcome Message"

        command_delete_welcome = u"Delete Welcome Message"

        command_edit_admin = u"Edit the admin list"
        command_edit_admin_1_description = \
            u"Fill out this form to edit the list of users who have " \
            u"administrative privileges."
        field_admin_jids = u"The admin list"

        command_restart = u"Restart the service"
        command_restart_1_description = \
            u"Fill out this form to restart the service."
        field_restart_delay = u"Delay before restarting the service"

        command_shutdown = u"Shut down the service"
        command_shutdown_1_description = \
            u"Fill out this form to shut down the service."
        field_shutdown_delay = u"Delay before shutting down the service"

        field_30_sec = u"30 seconds"
        field_60_sec = u"60 seconds"
        field_90_sec = u"90 seconds"
        field_120_sec = u"120 seconds"
        field_180_sec = u"180 seconds"
        field_240_sec = u"240 seconds"
        field_300_sec = u"300 seconds"

        welcome_message_subject = u"Welcome"

        account_disabled = u"This account is disabled"
        account_error = u"This account has an error"

        help_message_subject = u"Help"
        help_message_body = u"No help"

        command_last_error = u"Get account's last error"
        field_last_error = u"Last error"
        account_no_error = u"This account has no error"

    class fr(en):
        component_name = u"composant générique Jabber Component Library"
        register_title = u"Enregistrement d'un nouveau compte"
        register_instructions = u"Entrer les paramètres du compte"
        message_status = u" comptes enregistrés."
        account_name = u"Nom du compte"

        password_saved_for_session = u"Le mot de passe sera garder tout au " \
                                     u"long de la session Jabber."
        ask_password_subject = u"Demande de mot de passe"
        ask_password_body = u"Répondre à ce message avec le mot de passe " \
                            u"du compte %s\n"
        new_account_message_subject = u"Le compte '%s' a été créé"
        new_account_message_body = u"Compte créé"
        update_account_message_subject = u"Le compte '%s' a été mis " \
                                         u"à jour"
        update_account_message_body = u"Compte mis à jour"

        mandatory_field = u"%s est requis"
        not_well_formed_field = u"Le champs %s n'est pas acceptable"

        field_chat_action = u"Action lorsque l'état est 'Free For Chat'"
        field_online_action = u"Action lorsque l'état est 'Online'"
        field_away_action = u"Action lorsque l'état est 'Away'"
        field_xa_action = u"Action lorsque l'état est 'Not Available'"
        field_dnd_action = u"Action lorsque l'état est 'Do not Disturb'"
        field_offline_action = u"Action lorsque l'état est 'Offline'"

        field_action_0 = u"Ne rien Faire"
        field_chat_action_0 = field_action_0
        field_online_action_0 = field_action_0
        field_away_action_0 = field_action_0
        field_xa_action_0 = field_action_0
        field_dnd_action_0 = field_action_0
        field_offline_action_0 = field_action_0

        field_user_jid = u"JID utilisateur"
        field_password = u"Mot de passe"

        error_subject = u"Erreur"
        error_body = u"Une erreur est survenue :\n\t%s"

        get_gateway_desc = u"Entrer l'adresse email de votre contact"
        get_gateway_prompt = u"Adresse email"

        command_add_user = u"Créer un nouveau compte"
        command_add_user_1_description = u"Selectionner un type de compte"
        field_account_type = u"Type de compte"

        command_delete_user = u"Supprimer des comptes"
        command_delete_user_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s) pour" \
            u" rechercher le(s) compte(s) à supprimer"
        command_delete_user_2_description = u"Sélectionner le(s) compte(s) à " \
            u"supprimer"
        field_users_jids = u"Jabber ID(s) utilisateur(s)"
        field_account = u"Compte"
        field_accounts = u"Comptes"

        command_disable_user = u"Désactiver des comptes"
        command_disable_user_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s) " \
            u"pour rechercher le(s) compte(s) à désactiver"
        command_disable_user_2_description = u"Sélectionner le(s) compte(s) à" \
                                             u" désactiver"

        command_reenable_user = u"Réactiver des comptes"
        command_reenable_user_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s) " \
            u"pour rechercher le(s) compte(s) à réactiver"
        command_reenable_user_2_description = u"Sélectionner le(s) compte(s)" \
                                              u" à réactiver"

        command_end_user_session = u"Terminer des sessions utilisateurs"
        command_end_user_session_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s)" \
            u" pour rechercher le(s) session(s) à terminer"
        command_end_user_session_2_description = \
            u"Sélectionner le(s) compte(s) des sessions à terminer"

        command_get_user_password = u"Récupérer le mot de passe d'un compte"
        command_get_user_password_1_description = \
            u"Remplir ce formulaire avec le Jabber ID utilisateur" \
            u" pour rechercher le compte pour récupérer leur mot de passe"
        command_get_user_password_2_description = \
            u"Sélectionner le compte pour récupérer leur mot de passe"

        command_change_user_password = u"Changer le mot de passe d'un compte"
        command_change_user_password_1_description = \
            u"Remplir ce formulaire avec le Jabber ID utilisateur" \
            u" pour rechercher le compte pour changer leur mot de passe"
        command_change_user_password_2_description = \
            u"Sélectionner le compte pour changer leur mot de passe"

        command_get_user_roster = u"Récupérer les comptes utilisateurs"
        command_get_user_roster_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s)" \
            u" pour rechercher le(s) compte(s) à récupérer"

        command_get_user_lastlogin = u"Récupérer la date de derniere connexion"
        command_get_user_lastlogin_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s)" \
            u" pour rechercher le(s) compte(s) pour récupérer leur dernière " \
            u"date de connexion"
        command_get_user_lastlogin_2_description = \
            u"Sélectionner le compte pour récupérer la date de dernière connexion"

        command_get_registered_users_num = u"Récupérer de nombre de comptes " \
                                           u"enregistrés"
        command_get_disabled_users_num = u"Récupérer le nombre de comptes " \
                                         u"désactivés"
        command_get_online_users_num = u"Récupérer le nombre de comptes " \
                                       u"en ligne"

        command_get_registered_users_list = u"Récupérer la liste des comptes " \
                                           u"enregistrés"
        command_get_disabled_users_list = u"Récupérer la list des comptes " \
                                          u"désactivés"
        command_get_online_users_list = u"Récupérer la list des comptes " \
                                        u"en ligne"

        field_registered_users_num = u"Le nombre de comptes enregistrés"
        field_disabled_users_num = u"Le nombre de comptes désactivés"
        field_online_users_num = u"Le nombre de comptes connectés"

        field_max_items = u"Maximum d'éléments à récupérer"
        field_registered_users_list = u"La liste des comptes enregistrés"
        field_disabled_users_list = u"La liste des comptes désactivés"
        field_online_users_list = u"La liste des comptes connectés"

        command_announce = u"Faire une annonce"
        command_announce_1_description = \
            u"Remplir ce formulaire avec le(s) Jabber ID(s) utilisateur(s)" \
            u" à qui envoyer l'annonce"
        field_announcement = u"Annonce"

        command_set_motd = u"Écrire le Message Du Jour"
        command_set_motd_1_description = \
            u"Remplir ce formulaire avec le Message Du Jour à envoyer à tous" \
            u" les utilisateurs enregistrés"
        field_motd = u"Message Du Jour"

        command_edit_motd = u"Editer le Message Du Jour"

        command_delete_motd = u"Supprimer le Message Du Jour"

        command_set_welcome = u"Écrire le message de bienvenue"
        command_set_welcome_1_description = \
            u"Remplir ce formulaire avec le message de bienvenue à envoyer à" \
            u" tous les nouveaux utilisateurs"
        field_welcome = u"Message de bienvenue"

        command_delete_welcome = u"Supprimer le message de bienvenue"

        command_edit_admin = u"Editer la liste des administrateurs"
        command_edit_admin_1_description = \
            u"Remplir ce formulaire pour éditer la liste des utilisateurs qui" \
            u" ont les privilèges d'administration du service."
        field_admin_jids = u"La liste des administrateur"

        command_restart = u"Redémarrer le service"
        command_restart_1_description = \
            u"Remplir ce formulaire pour redémarrer le service."
        field_restart_delay = u"Délai avant de redémarrer le service"

        command_shutdown = u"Arrêter le service"
        command_shutdown_1_description = \
            u"Remplir ce formulaire pour arrêter le service."
        field_shutdown_delay = u"Délai avant d'arrêter le service"

        field_30_sec = u"30 secondes"
        field_60_sec = u"60 secondes"
        field_90_sec = u"90 secondes"
        field_120_sec = u"120 secondes"
        field_180_sec = u"180 secondes"
        field_240_sec = u"240 secondes"
        field_300_sec = u"300 secondes"

        welcome_message_subject = u"Bienvenue"

        account_disabled = u"Ce compte est désactivé"
        account_error = u"Ce compte est en erreur"

        help_message_subject = u"Aide"
        help_message_body = u"Pas d'aide !"

        command_last_error = u"Récupérer la dernière erreur du compte"
        field_last_error = u"Dernière erreur"
        account_no_error = u"Ce compte n'a pas d'erreur"

    class nl(en):
        # TODO: when finish, delete this line and uncomment in tests/lang.py the makeSuite(Language_nl_TestCase, 'test') line
        register_title = u"Registratie van verbindingen voor Jabber Mail"
        register_instructions = u"Instellingen voor verbinding"
        account_name = u"Accountnaam"
        account_login = u"Gebruikersnaam"
        account_password = u"Wachtwoord"
        account_password_store = u"Wachtwoord opslaan op Jabber-server?"
        account_host = u"Server"
        account_port = u"Poort"
        account_type = u"Soort account"
        account_mailbox = u"Pad naar mailbox (IMAP)"
        account_ffc_action = u"Actie bij aanwezigheid 'Chat'"
        account_online_action = u"Actie bij aanwezigheid 'Beschikbaar'"
        account_away_action = u"Actie bij aanwezigheid 'Afwezig'"
        account_xa_action = u"Actie bij aanwezigheid 'Langdurig afwezig'"
        account_dnd_action = u"Actie bij aanwezigheid 'Niet storen'"
        account_offline_action = u"Actie bij aanwezigheid 'Niet beschikbaar'"
        account_check_interval = u"Controle-interval (in minuten)"
        account_live_email_only = u"Enkel controleren op e-mails als er een" \
                                  "verbinding is met Jabber"
        action_nothing = u"Niets doen"
        action_retrieve = u"E-mail ophalen"
        action_digest = u"Samenvatting verzenden"
        update_title = u"Bijwerken van JMC"
        update_instructions = u"Verbinding '%s' aanpassen"
        connection_label = u"%s verbinding '%s'"
#        update_account_message_subject = u"Verbinding %s '%s' werd bijgewerkt"
        update_account_message_body = u"Geregistreerd met gebruikersnaam '%s'"\
                                      u"en wachtwoord '%s' op '%s'"
#         new_account_message_subject = u"Nieuwe %s verbinding '%s' aangemaakt"
        new_account_message_body = u"Geregistreerd met " \
                                   u"gebruikersnaam '%s' en wachtwoord " \
                                   u"'%s' op '%s'"
        ask_password_subject = u"Wachtwoordaanvraag"
#         ask_password_body = u"Antwoord dit bericht met het volgende " \
#                             u"wachtwoord voor de volgende account: \n" \
#                             u"\thost = %s\n" \
#                             u"\tlogin = %s\n"
        password_saved_for_session = u"Het wachtwoord zal worden bewaard " \
                                     u"tijdens uw Jabber-sessie"
        check_error_subject = u"Fout tijdens controle op e-mails."
        check_error_body = u"Fout tijdens controle op e-mails:\n\t%s"
        new_mail_subject = u"Nieuwe e-mail van %s"
        new_digest_subject = u"%i nieuwe e-mail(s)"

    class es(en):
        # TODO: when finish, delete this line and uncomment in tests/lang.py the makeSuite(Language_es_TestCase, 'test') line
        register_title = u"Registro de nueva cuenta de email"
        register_instructions = u"Inserta los datos para la nueva cuenta"
        account_name = u"Nombre para la cuenta"
        account_login = u"Usuario (login)"
        account_password = u"Contraseña"
        account_password_store = u"¿Guardar la contraseña en el servidor " \
                                 u"Jabber?"
        account_host = u"Host"
        account_port = u"Puerto"
        account_type = u"Tipo de servidor Mail"
        account_mailbox = u"Ruta del mailbox (solo para IMAP)"
        account_ffc_action = u"Acción para cuando tu estado sea " \
                             u"'Listopara hablar'"
        account_online_action = u"Acción para cuando tu estado sea 'Conectado'"
        account_away_action = u"Acción para cuando tu estado sea 'Ausente'"
        account_xa_action = u"Acción para cuando tu estado sea 'No disponible'"
        account_dnd_action = u"Acción para cuando tu estado sea 'No molestar'"
        account_offline_action = u"Acción para cuando tu estado sea " \
                                 u"'Desconectado'"
        account_check_interval = u"Intervalo para comprobar emails nuevos " \
                                 u"(en minutos)"
        account_live_email_only = u"Avisarme de emails nuevos solo cuando " \
                                  u"esté conectado"
        action_nothing = u"No hacer nada"
        action_retrieve = u"Mostrarme el email"
        action_digest = u"Enviar resúmen"
        update_title = u"Actualización de cuenta de email"
        update_instructions = u"Modifica los datos de la cuenta '%s'"
        connection_label = u"%s conexión '%s'"
#        update_account_message_subject = u"Actualizada %s conexión '%s'"
        update_account_message_body = u"Registrado con el usuario '%s' y " \
                                      u"contraseña '%s' en '%s'"
#        new_account_message_subject = u"Nueva %s conexión '%s' creada"
        new_account_message_body = u"Registrado con usuario '%s' y " \
                                   u"contraseña '%s' en '%s'"
        ask_password_subject = u"Petición de contraseña"
#         ask_password_body = u"Para avisarte de emails nuevos, contesta a " \
#                             u"este mensaje con la contraseña " \
#                             u"de la cuenta: \n" \
#                             u"\tHost = %s\n" \
#                             u"\tUsuario = %s\n"
        password_saved_for_session = u"La contraseña será guardada para " \
                                     u"esta sesión únicamente."
        check_error_subject = u"Error al revisar los emails."
        check_error_body = u"Un error apareció al revisar los emails:\n\t%s"
        new_mail_subject = u"Nuevo email en %s"
        new_digest_subject = u"%i email(s) nuevo(s)"

    class pl(en):
        # TODO: when finish, delete this line and uncomment in tests/lang.py the makeSuite(Language_pl_TestCase, 'test') line
        register_title = u"Rejestracja w komponencie E-Mail"
        register_instructions = u"Wprowadź parametry połączenia"
        account_name = u"Nazwa połączenia"
        account_login = u"Nazwa użytkownika"
        account_password = u"Hasło"
        account_password_store = u"Zachować hasło na serwerze Jabbera? "
        account_host = u"Nazwa hosta"
        account_port = u"Port"
        account_type = u"Typ serwera email"
        account_mailbox = u"Ścieżka do skrzynki odbiorczej (IMAP)"
        account_ffc_action = u"Akcja gdy status to 'Chętny do rozmowy'"
        account_online_action = u"Akcja gdy status to 'Dostępny'"
        account_away_action = u"Akcja gdy status to 'Zaraz wracam'"
        account_xa_action = u"Akcja gdy status to 'Niedostępny'"
        account_dnd_action = u"Akcja gdy status to 'Nie przeszkadzać'"
        account_offline_action = u"Akcja gdy status to 'Rozłączony'"
        account_check_interval = u"Sprawdzaj email co (w minutach)"
        account_live_email_only = u"Raportuj otrzymane emaile tylko\n gdy " \
                                  u"podłączony do Jabbera"
        action_nothing = u"Nic nie rób"
        action_retrieve = u"Pobierz emaila"
        action_digest = u"Wyślij zarys emaila"
        update_title = u"Modyfikacja połączenia z komponentem mailowym"
        update_instructions = u"Modyfikacja połączenia '%s'"
        connection_label = u"%s połączenie '%s'"
#        update_account_message_subject = u"Zmodyfikowane %s połączenie '%s'"
        update_account_message_body = u"Zarejestrowany z nazwą użytkownika " \
                                      u"'%s' i hasłem '%s' na '%s'"
#        new_account_message_subject = u"Nowe %s połączenie '%s' utworzone"
        new_account_message_body = u"Zarejestrowany z nazwą użytkownika " \
                                   u"'%s' i hasłem '%s' na '%s'"
        ask_password_subject = u"Żądanie hasła"
#         ask_password_body = u"Odpowiedz na ta wiadomosc z hasłem dla " \
#                             u"podanego konta: \n" \
#                             u"\tnazwa hosta = %s\n" \
#                             u"\tnazwa uzytkownika = %s\n"
        password_saved_for_session = u"Hasło będzie przechowywane podczas " \
                                     u"Twojej sesji Jabbera"
        check_error_subject = u"Błąd podczas sprawdzania emaili."
        check_error_body = u"Pojawił się błąd podczas sprawdzania " \
                           u"emaili:\n\t%s"
        new_mail_subject = u"Nowy email od %s"
        new_digest_subject = u"%i nowy(ch) email(i)"

    class cs(en):
        # TODO: when finish, delete this line and uncomment in tests/lang.py the makeSuite(Language_cs_TestCase, 'test') line
        register_title = u"Jabber MailNotify registrace"
        register_instructions = u"Vložte nastavení spojení"
        account_name = u"Název spojení"
        account_login = u"Přihlašovací jméno"
        account_password = u"Heslo"
        account_password_store = u"Uložit heslo na Jabber serveru?"
        account_host = u"Poštovní server"
        account_port = u"Port"
        account_type = u"Typ poštovního serveru"
        account_mailbox = u"Cesta IMAP schránky"
        account_ffc_action = u"Akce při statusu 'Ukecaný'"
        account_online_action = u"Akce při statusu 'Přítomen'"
        account_away_action = u"Akce při statusu 'Pryč'"
        account_xa_action = u"Akce při statusu 'Nepřítomen'"
        account_dnd_action = u"Akce při statusu 'Nerušit'"
        account_offline_action = u"Akce při statusu 'Odpojen'"
        account_check_interval = u"Interval kontroly pošty (v minutách)"
        account_live_email_only = u"Informuj pouze o emailech, které přišly během připojení k Jabberu"
        action_nothing = u"Nedělej nic"
        action_retrieve = u"Přijmi poštu"
        action_digest = u"Pošli upozornění na novou poštu"
        update_title = u"Jabber - aktualizace spojení k emailu"
        update_instructions = u"Aktualizace spojení '%s'"
        connection_label = u"%s spojení '%s'"
#        update_account_message_subject = u"Aktualizováno %s spojení '%s'"
        update_account_message_body = u"Registrováno s přihlašovacím jménem '%s' a " \
                                      u"heslem '%s' v '%s'"
#        new_account_message_subject = u"Nové spojení %s '%s' aktualizováno"
        new_account_message_body = u"Registrováno " \
                                   u"s přihlašovacím jménem '%s' a heslem '%s' v '%s'"
        ask_password_subject = u"Žádost o heslo"
#         ask_password_body = u"Odpovězte na tuto zprávu posláním hesla " \
#                             u"pro následující spojení: \n" \
#                             u"\thost = %s\n" \
#                             u"\tlogin = %s\n"
        password_saved_for_session = u"Heslo bude uchováno během vašeho připojení k Jabberu"
        check_error_subject = u"Chyba při kontrole emailů."
        check_error_body = u"Nějaká chyba nastala při kontrole emailů:\n\t%s"
        new_mail_subject = u"Nový email od %s"
        new_digest_subject = u"%i má nový(é) email(y)"

    class ru(en):
        # TODO: when finish, delete this line and uncomment in tests/lang.py the makeSuite(Language_ru_TestCase, 'test') line
        register_title = u"Учетные данные соединения"
        register_instructions = u"Введите данные для соединения"
        account_name = u"Имя соединения"
        account_login = u"Логин@gmail.ru"
        account_password = u"Пароль"
        account_password_store = u"Сохранять пароль на сервере?"
        account_host = u"Хост"
        account_port = u"Порт (обычно, 110)"
        account_type = u"Тип учетной записи"
        account_mailbox = u"Путь к почтовому ящику (IMAP)"
        account_ffc_action = u"Действие для состояния 'Free For Chat'"
        account_online_action = u"Действие для состояния 'Online'"
        account_away_action = u"Действие для состояния 'Away'"
        account_xa_action = u"Действие для состояния 'Not Available'"
        account_dnd_action = u"Действие для состояния 'Do not Disturb'"
        account_offline_action = u"Действие для состояния 'Offline'"
        account_check_interval = u"Интервал проверки почты (в минутах)"
        account_live_email_only = u"Сообщать о письмах только на момент подключения"
        action_nothing = u"Не делать ничего"
        action_retrieve = u"Показать почту"
        action_digest = u"Показать уведомление"
        update_title = u"Уточнение параметров"
        update_instructions = u"Изменяем соединение '%s'"
        connection_label = u"%s соединение '%s'"
#        update_account_message_subject = u"Данные для  %s обновлены '%s'"
        update_account_message_body = u"Зарегистрирован с логином '%s' и " \
                                      u"паролем '%s' на '%s'"
#        new_account_message_subject = u"Новое %s соединение '%s' создано"
        new_account_message_body = u"Перерегистрирован с " \
                                   u"логином '%s' и паролем '%s' на '%s'"
        ask_password_subject = u"Запрос пароля"
#         ask_password_body = u"Ответьте на это сообщение с паролем " \
#                             u"для следующей учетной записи: \n" \
#                             u"\tХост = %s\n" \
#                             u"\tЛогин = %s\n"
        password_saved_for_session = u"Пароль будет сохранен только на время Вашей сессии."
        check_error_subject = u"Ошибка при проверке почты."
        check_error_body = u"Возникла ошибка при проверке почты:\n\t%s"
        new_mail_subject = u"Новая почта от %s"
        new_digest_subject = u"%i новое(ые) письмо(а)"
