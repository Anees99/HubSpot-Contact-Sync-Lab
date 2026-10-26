import copy
import unittest
from sync_lab.core import *
ROW={'external_id':'a','email':' Alice@Example.com ','firstname':'Alice','phone':'+92 300 0000001'}
class SyncTests(unittest.TestCase):
    def test_normalization(self):self.assertEqual(clean(ROW)['email'],'alice@example.com')
    def test_phone(self):self.assertEqual(clean(ROW)['phone'],'+923000000001')
    def test_invalid_phone(self):
        with self.assertRaises(ValueError):clean({**ROW,'phone':'0300123'})
    def test_unknown_columns(self):
        with self.assertRaises(ValueError):clean({**ROW,'token':'secret'})
    def test_empty_id(self):
        with self.assertRaises(ValueError):clean({**ROW,'external_id':''})
    def test_bad_email(self):self.assertEqual(plan([{**ROW,'email':'bad'}])['summary']['rejected_rows'],1)
    def test_exact_duplicates(self):self.assertEqual(plan([ROW,ROW])['summary']['duplicate_rows_skipped'],1)
    def test_id_conflict_quarantines_both(self):self.assertEqual(plan([ROW,{**ROW,'firstname':'Changed'}])['summary']['planned_contacts'],0)
    def test_email_conflict_quarantines_both(self):self.assertEqual(plan([ROW,{**ROW,'external_id':'b'}])['summary']['planned_contacts'],0)
    def test_custom_unique_key(self):self.assertEqual(plan([ROW])['batches'][0]['inputs'][0]['idProperty'],PROPERTY)
    def test_blank_not_clear(self):self.assertNotIn('lastname',plan([{**ROW,'lastname':''}])['batches'][0]['inputs'][0]['properties'])
    def test_batching(self):
        p=plan([{**ROW,'external_id':str(i),'email':f'a{i}@example.com'} for i in range(101)])
        self.assertEqual([len(b['inputs']) for b in p['batches']],[100,1])
    def test_bad_batch_size(self):
        for n in [0,101,True]:
            with self.assertRaises(ValueError):plan([ROW],n)
    def test_deterministic_hash(self):self.assertEqual(plan([ROW])['plan_sha256'],plan([ROW])['plan_sha256'])
    def test_header_duplicate(self):
        with self.assertRaises(ValueError):read_csv('external_id,email,email\na,a@x.com,b@x.com')
    def test_missing_header(self):
        with self.assertRaises(ValueError):read_csv('email\na@x.com')
    def test_response_partial(self):
        b=plan([ROW])['batches'][0]
        self.assertEqual(reconcile(b,{'status':'COMPLETE','results':[]})['needs_review'],['a'])
    def test_response_success(self):
        b=plan([ROW])['batches'][0];r={'status':'COMPLETE','results':[{'id':'1','properties':{PROPERTY:'a'}}]}
        self.assertEqual(reconcile(b,r)['confirmed'],['a'])
    def test_pending_is_not_success(self):
        b=plan([ROW])['batches'][0];r={'status':'PENDING','results':[{'id':'1','properties':{PROPERTY:'a'}}]}
        self.assertEqual(reconcile(b,r)['confirmed'],[])
    def test_errors_require_review(self):
        b=plan([ROW])['batches'][0];r={'status':'COMPLETE','errors':[{}],'results':[{'id':'1','properties':{PROPERTY:'a'}}]}
        self.assertEqual(reconcile(b,r)['confirmed'],[])
    def test_retry_after(self):self.assertEqual(retry_policy(429,1,30)['delay_seconds'],30)
    def test_no_auth_retry(self):self.assertFalse(retry_policy(401,1)['retry'])
    def test_retry_bound(self):self.assertFalse(retry_policy(503,3)['retry'])
    def test_request_contract(self):self.assertEqual(request_contract(plan([ROW])['batches'][0])['method'],'POST')
