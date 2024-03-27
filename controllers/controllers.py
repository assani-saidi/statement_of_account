# -*- coding: utf-8 -*-
# from odoo import http


# class Invoice(http.Controller):
#     @http.route('/invoice/invoice', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/invoice/invoice/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('invoice.listing', {
#             'root': '/invoice/invoice',
#             'objects': http.request.env['invoice.invoice'].search([]),
#         })

#     @http.route('/invoice/invoice/objects/<model("invoice.invoice"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('invoice.object', {
#             'object': obj
#         })
