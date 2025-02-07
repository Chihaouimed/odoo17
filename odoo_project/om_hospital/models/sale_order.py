from odoo import models, fields

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    x_extra_info = fields.Char(string="Additional Information")

class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    x_extra = fields.Char(string="Additional Information")
