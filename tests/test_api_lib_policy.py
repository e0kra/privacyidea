"""
This test file tests the api.lib.policy.py

The api.lib.policy.py depends on lib.policy and on flask!
"""
import json
from .base import MyTestCase

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    PolicyClass, SCOPE)
from privacyidea.api.lib.policy import (check_serial, check_tokentype,
                                        no_detail_on_success,
                                        no_detail_on_fail,
                                        check_token_upload,
                                        check_base_action, check_token_init,
                                        check_max_token_user,
                                        check_max_token_realm)
from privacyidea.lib.token import (init_token, get_tokens, remove_token,
                                   set_realms)
from privacyidea.lib.user import User

from flask import Response, Request, g
from werkzeug.test import EnvironBuilder
from privacyidea.lib.error import PolicyError


class PrePolicyDecoratorTestCase(MyTestCase):

    def test_01_check_token_action(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        req.all_data = {"serial": "SomeSerial"}

        # Set a policy, that does allow the action
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enable", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # Action enable is cool
        r = check_base_action(request=req, action="enable")
        self.assertTrue(r)

        # Another action - like "disable" - is not allowed
        # An exception is
        self.assertRaises(PolicyError,
                          check_base_action, req, "disable")

        # A normal user can "disable", since no user policies are defined.
        g.logged_in_user = {"username": "user1",
                            "role": "user"}
        r = check_base_action(req, "disable")
        self.assertTrue(r)
        delete_policy("pol1")

    def test_02_check_token_init(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        req.all_data = {"type": "totp"}

        # Set a policy, that does allow the action
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enrollTOTP, enrollHOTP",
                   client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # Enrolling TOTP is cool
        r = check_token_init(req)
        self.assertTrue(r)

        # Another Token type can not be enrolled:
        # An exception is raised
        req.all_data = {"type": "motp"}
        self.assertRaises(PolicyError,
                          check_token_init, req)

        # A normal user can "enroll", since no user policies are defined.
        g.logged_in_user = {"username": "user1",
                            "role": "user"}
        r = check_token_init(req)
        self.assertTrue(r)
        # finally delete policy
        delete_policy("pol1")


    def test_03_check_token_upload(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        req.all_data = {"filename": "token.xml"}

        # Set a policy, that does allow the action
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enrollTOTP, enrollHOTP, import",
                   client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # Try to import tokens
        r = check_token_upload(req)
        self.assertTrue(r)

        # The admin can not upload from another IP address
        # An exception is raised
        env["REMOTE_ADDR"] = "192.168.0.1"
        req = Request(env)
        req.all_data = {"filename": "token.xml"}
        self.assertRaises(PolicyError,
                          check_token_upload, req)
        # finally delete policy
        delete_policy("pol1")

    def test_04_check_max_token_user(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1}

        # Set a policy, that allows two tokens per user
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="max_token_per_user=2")
        g.policy_object = PolicyClass()
        # The user has one token, everything is fine.
        self.setUp_user_realms()
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": "1234567890123456"},
                                  user=User(login="cornelius",
                                            realm=self.realm1))
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 1)
        self.assertTrue(check_max_token_user(req))

        # Now the user gets his second token
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": "1234567890123456"},
                                  user=User(login="cornelius",
                                            realm=self.realm1))
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 2)

        # The user has two tokens. The check that will run in this case,
        # before the user would be assigned the 3rd token, will raise a
        # PolicyError
        self.assertRaises(PolicyError,
                          check_max_token_user, req)

        # finally delete policy
        delete_policy("pol1")
        remove_token("NEW001")
        remove_token("NEW002")

    def test_05_check_max_token_realm(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        req.all_data = {"realm": self.realm1}

        # Set a policy, that allows two tokens per realm
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="max_token_per_realm=2",
                   realm=self.realm1)
        g.policy_object = PolicyClass()
        self.setUp_user_realms()
        # Add the first token into the realm
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": "1234567890123456"})
        set_realms("NEW001", [self.realm1])
        # check the realm, only one token is in it the policy condition will
        # pass
        tokenobject_list = get_tokens(realm=self.realm1)
        self.assertTrue(len(tokenobject_list) == 1)
        self.assertTrue(check_max_token_realm(req))

        # add a second token to the realm
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": "1234567890123456"})
        set_realms("NEW002", [self.realm1])
        tokenobject_list = get_tokens(realm=self.realm1)
        self.assertTrue(len(tokenobject_list) == 2)

        # request with a user object, not with a realm
        req.all_data = {"user": "cornelius@%s" % self.realm1}

        # Now a new policy check will fail, since there are already two
        # tokens in the realm
        self.assertRaises(PolicyError,
                          check_max_token_realm, req)

        # finally delete policy
        delete_policy("pol1")
        remove_token("NEW001")
        remove_token("NEW002")


class PostPolicyDecoratorTestCase(MyTestCase):

    def test_01_check_tokentype(self):
        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "PISP0000AB00",
                          "type": "spass"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=hotp", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_tokentype,
                          req, resp)

        # A policy, that allows the token spass
        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=spass", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        #  is raised.
        r = check_tokentype(req, resp)
        jresult = json.loads(r.data)
        self.assertTrue(jresult.get("result").get("value"))

    def test_02_check_serial(self):
        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="serial=TOTP", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token serial HOTP is not allowed on this client, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_serial,
                          req, resp)

        # A policy, that allows the token spass
        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="serial=HOTP", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        # is raised.
        r = check_serial(req, resp)
        jresult = json.loads(r.data)
        self.assertTrue(jresult.get("result").get("value"))

    def test_03_no_detail_on_success(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_success", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_success(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" not in jresult, jresult)
        delete_policy("pol2")

    def test_04_no_detail_on_fail(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_fail", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_fail(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" not in jresult, jresult)

        # A successful call has a detail in the response!
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        new_response = no_detail_on_fail(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" in jresult, jresult)

        delete_policy("pol2")