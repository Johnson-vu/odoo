# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# Python bytecode 2.7 (62211)
# Embedded file name: /opt/lamthao/server/openerp/addons/account/account_financial_report.py
# Compiled at: 2014-02-08 10:27:56
# Decompiled by https://python-decompiler.com
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class account_financial_report(osv.osv):
    _name = 'account.financial.report'
    _description = 'Account Report'

    def _get_level(self, cr, uid, ids, field_name, arg, context=None):
        """Returns a dictionary with key=the ID of a record and value = the level of this  
            record in the tree structure."""
        res = {}
        for report in self.browse(cr, uid, ids, 1=context):
            level = 0
            if report.parent_id:
                level = report.parent_id.level + 1
            res[report.id] = level

        return res

    def _get_children_by_order(self, cr, uid, ids, context=None):
        """returns a dictionary with the key= the ID of a record and value = all its children,
           computed recursively, and sorted by sequence. Ready for the printing"""
        res = []
        for id in ids:
            res.append(id)
            ids2 = self.search(cr, uid, [('parent_id', '=', id)], 3='sequence ASC', 5=context)
            res += self._get_children_by_order(cr, uid, ids2, 5=context)

        return res

    def _get_balance(self, cr, uid, ids, field_names, args, context=None):
        """returns a dictionary with key=the ID of a record and value=the balance amount 
           computed for this record. If the record is of type\xa0:
               'accounts'\xa0: it's the sum of the linked accounts
               'account_type'\xa0: it's the sum of leaf accoutns with such an account_type
               'account_report'\xa0: it's the amount of the related report
               'sum'\xa0: it's the sum of the children of this record (aka a 'view' record)"""
        account_obj = self.pool.get('account.account')
        res = {}
        for report in self.browse(cr, uid, ids, 2=context):
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in field_names)
            if report.type == 'accounts':
                for a in report.account_ids:
                    for field in field_names:
                        res[report.id][field] += getattr(a, field)

            elif report.type == 'account_type':
                report_types = [ x.id for x in report.account_type_ids ]
                account_ids = account_obj.search(cr, uid, [('user_type', 'in', report_types), ('type', '!=', 'view')], 2=context)
                for a in account_obj.browse(cr, uid, account_ids, 2=context):
                    for field in field_names:
                        res[report.id][field] += getattr(a, field)

            elif report.type == 'account_report' and report.account_report_id:
                res2 = self._get_balance(cr, uid, [report.account_report_id.id], field_names, False, 2=context)
                for key, value in res2.items():
                    for field in field_names:
                        res[report.id][field] += value[field]

            elif report.type == 'sum':
                res2 = self._get_balance(cr, uid, [ rec.id for rec in report.children_ids ], field_names, False, 2=context)
                for key, value in res2.items():
                    for field in field_names:
                        res[report.id][field] += value[field]

        return res

    _columns = {'name': fields.char('Report Name', 6=128, 8=True, 9=True), 
       'parent_id': fields.many2one('account.financial.report', 'Parent'), 
       'children_ids': fields.one2many('account.financial.report', 'parent_id', 'Account Report'), 
       'sequence': fields.integer('Sequence'), 
       'balance': fields.function(_get_balance, 'Balance', 17='balance'), 
       'debit': fields.function(_get_balance, 'Debit', 17='balance'), 
       'credit': fields.function(_get_balance, 'Credit', 17='balance'), 
       'level': fields.function(_get_level, 23='Level', 25=True, 26='integer'), 
       'type': fields.selection([
              ('sum', 'View'),
              ('accounts', 'Accounts'),
              ('account_type', 'Account Type'),
              ('account_report', 'Report Value')], 'Type'), 
       'account_ids': fields.many2many('account.account', 'account_account_financial_report', 'report_line_id', 'account_id', 'Accounts'), 
       'account_report_id': fields.many2one('account.financial.report', 'Report Value'), 
       'account_type_ids': fields.many2many('account.account.type', 'account_account_financial_report_type', 'report_id', 'account_type_id', 'Account Types'), 
       'sign': fields.selection([(-1, 'Reverse balance sign'), (1, 'Preserve balance sign')], 'Sign on Reports', 8=True, 55='For accounts that are typically more debited than credited and that you would like to print as negative amounts in your reports, you should reverse the sign of the balance; e.g.: Expense account. The same applies for accounts that are typically more credited than debited and that you would like to print as positive amounts in your reports; e.g.: Income account.'), 
       'display_detail': fields.selection([
                        ('no_detail', 'No detail'),
                        ('detail_flat', 'Display children flat'),
                        ('detail_with_hierarchy', 'Display children with hierarchy')], 'Display details'), 
       'style_overwrite': fields.selection([
                         (0, 'Automatic formatting'),
                         (1, 'Main Title 1 (bold, underlined)'),
                         (2, 'Title 2 (bold)'),
                         (3, 'Title 3 (bold, smaller)'),
                         (4, 'Normal Text'),
                         (5, 'Italic Text (smaller)'),
                         (6, 'Smallest Text')], 'Financial Report Style', 55="You can set up here the format you want this record to be displayed. If you leave the automatic formatting, it will be computed based on the financial reports hierarchy (auto-computed field 'level').")}
    _defaults = {'type': 'sum', 
       'display_detail': 'detail_flat', 
       'sign': 1, 
       'style_overwrite': 0}


account_financial_report()