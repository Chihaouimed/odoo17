from odoo import api, fields, models

class HospitalPatient(models.Model):
    _name= 'hospital.patient'
    _description= 'patient master'

    name = fields.Char(string='name', required=True)
    date_of_birth = fields.Date(string='DOB')
    gender = fields.Selection([('male', 'Male'),('female', 'Female')], string='Gender')