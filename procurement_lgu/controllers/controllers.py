# -*- coding: utf-8 -*-
from odoo import http

# class Budgeting(http.Controller):
#     @http.route('/budgeting/budgeting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/budgeting/budgeting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('budgeting.listing', {
#             'root': '/budgeting/budgeting',
#             'objects': http.request.env['budgeting.budgeting'].search([]),
#         })

#     @http.route('/budgeting/budgeting/objects/<model("budgeting.budgeting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('budgeting.object', {
#             'object': obj
#         })