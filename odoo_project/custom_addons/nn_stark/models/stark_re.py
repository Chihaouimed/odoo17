from odoo import api, fields, models, _
from datetime import datetime


class Commercial(models.Model):
    _name = 'crm.commercial'

    name = fields.Char(string="Nom & Prénom", required=True)
    telephone = fields.Char(string="Téléphone")
    mail = fields.Char(string="E-mail")
    apporteur_affaire_user = fields.Boolean(string="Apporteur d’affaire")
    conseille_user = fields.Boolean(string="Conseiller")
    coordinateur_technique_user = fields.Boolean(string="Coordinateur technique")
    charge_etude_user = fields.Boolean(string="Chargé d’étude")
    installateur_user = fields.Boolean(string="Installateur")


class DistrictSteg(models.Model):
    _name = 'district.steg'

    name = fields.Char(string="District STEG", required=True)


class CalibreDisjoncteur(models.Model):
    _name = 'calibre.disjoncteur'

    name = fields.Char(string="Calibre Disjoncteur", required=True)
    puissance = fields.Integer(string='Intensité (A)')


class ModulePV(models.Model):
    _name = 'module.pv'

    name = fields.Char(string="Référence Module PV", required=True)
    marque = fields.Char(string='Marque Module PV', required=True)
    puissance = fields.Integer(string='Puissance Module (Wc)', required=True)


class OnduleurPV(models.Model):
    _name = 'onduleur.pv'

    name = fields.Char(string="Référence Onduleur PV", required=True)
    marque = fields.Char(string='Marque Onduleur PV', required=True)
    puissance = fields.Integer(string='Puissance onduleur (kVA)', required=True)
    courant_sortie = fields.Integer(string='Calibre Disjoncteur Onduleur (A)', required=True)


class CrmStageSequence(models.Model):
    _inherit = "crm.stage"

    ordre = fields.Integer(string="Séquence")
    page_info_projet = fields.Boolean(string="Afficher page Info Projet")
    page_predimension = fields.Boolean(string="Afficher page Prédimensionnement")
    page_visite_site = fields.Boolean(string="Afficher page Visite de Site")
    page_chiffrage = fields.Boolean(string="Afficher page Chiffrage")
    page_instructions = fields.Boolean(string="Afficher page Instructions")


class CrmStageChangeHistory(models.Model):
    _name = 'crm.stage.change.history'
    _description = 'Historique des changements de stage'
    name = fields.Char()
    lead_id = fields.Many2one('crm.lead', string="Opportunité")
    stage_id = fields.Many2one('crm.stage', string="Stage")
    ordre_id = fields.Integer(related='stage_id.ordre')
    date_start = fields.Datetime(string="Date de début")
    date_end = fields.Datetime(string="Date de fin")
    duree = fields.Char(string="Durée", compute='_compute_duration')

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                start_date = fields.Datetime.from_string(record.date_start)
                end_date = fields.Datetime.from_string(record.date_end)
                duration_seconds = (end_date - start_date).total_seconds()
                days = duration_seconds // (24 * 3600)
                hours = (duration_seconds % (24 * 3600)) // 3600
                minutes = (duration_seconds % 3600) // 60
                record.duree = "{} jours, {} heures, {} minutes".format(int(days), int(hours), int(minutes))
            else:
                record.duree = ""

    @api.model
    def create(self, vals):
        # Auto-fill date_start on creation
        vals['date_start'] = fields.Datetime.now()
        return super(CrmStageChangeHistory, self).create(vals)

    def end_stage(self):
        for history in self:
            history.date_end = fields.Datetime.now()


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.depends('partner_id')
    def _compute_name(self):
        for lead in self:
            if not lead.name and lead.partner_id and lead.partner_id.name:
                lead.name = lead.partner_id.name

    seq = fields.Char(string='Sequence', copy=False, readonly=True,
                      default=lambda self: _('Nouveau'))

    # Sequence CRM
    # @api.model
    # def create(self, vals):
    #     if 'seq' not in vals or vals['seq'] == _('Nouveau'):
    #         vals['seq'] = self.env['ir.sequence'].next_by_code('crm.seq') or _('Nouveau')
    #     return super(CrmLead, self).create(vals)
    @api.depends('seq')
    def assign_new_sequence(self):
        for record in self:
            if not record.seq or record.seq == _('Nouveau'):
                record.seq = self.env['ir.sequence'].next_by_code('crm.seq') or _('Nouveau')

    apporteur_affaire = fields.Many2one('crm.commercial', string="Apporteur d'Affaire",
                                        domain="['|', ('apporteur_affaire_user', '=', True), ('conseille_user', '=', True)]")
    conseille = fields.Many2one('crm.commercial', string="Conseiller",
                                domain="['|', ('apporteur_affaire_user', '=', True), ('conseille_user', '=', True)]")
    type_installation = fields.Selection([('bt', 'Résidentiel BT'),
                                          ('cmbt', 'Commercial BT'),
                                          ('mt', 'Industriel MT')])
    district_steg = fields.Many2one('district.steg', string="District STEG")
    ref_steg = fields.Integer(string='Référence STEG', digits=(9, 0), group_operator=False)
    type_compteur = fields.Selection([('1', 'Monophasé'),
                                      ('2', 'Triphasé'),
                                      ], string='Type de compteur ', )
    calibre_disjoncteur_existant = fields.Many2one('calibre.disjoncteur', string="Calibre du disjoncteur existant (A)")
    puissance_disj_existant = fields.Integer(related='calibre_disjoncteur_existant.puissance')
    calibre_disjoncteur_steg = fields.Many2one('calibre.disjoncteur', string="Calibre du disjoncteur STEG (A)")
    puissance_disj_steg = fields.Integer(related='calibre_disjoncteur_steg.puissance')
    courbe_charge_stark = fields.Boolean(string="Courbe de charge STARK")
    facture_steg = fields.Boolean(string="Facture d’électricité STEG")
    state_calibre = fields.Selection([
        ('ras', 'RAS'),
        ('danger', 'A régulariser')],
        compute="_compute_state_calibre", string="Statut")

    @api.depends('puissance_disj_existant', 'puissance_disj_steg')
    def _compute_state_calibre(self):
        for record in self:
            if record.puissance_disj_steg != record.puissance_disj_existant:
                record.state_calibre = "danger"
            else:
                record.state_calibre = "ras"

    puissance_souscrite = fields.Float(string='Puissance souscrite (kW)',
                                       compute="_compute_puissance_souscrite")

    @api.onchange('type_compteur', 'puissance_disj_steg')
    def _compute_puissance_souscrite(self):
        for record in self:
            if record.type_compteur == '1':
                record.puissance_souscrite = record.puissance_disj_steg * 230 / 1000
            elif record.type_compteur == '2':
                record.puissance_souscrite = record.puissance_disj_steg * 400 * 1.732 / 1000
            else:
                record.puissance_souscrite = 0

    consommation_annuelle = fields.Integer(string='Consommation Annuelle (kWh)', digits=0)

    module_pv = fields.Many2one('module.pv', string='Référence Module PV')
    marque_module = fields.Char(related='module_pv.marque', string='Marque Module PV')
    puissance_module = fields.Integer(related='module_pv.puissance', string='Puissance module (Wc)')
    nombre_module = fields.Integer(string='Nombre de Modules')
    puissance_total = fields.Float(string='Puissance Total DC (kWc)', compute="_compute_puissance_total", store=True)

    @api.onchange('nombre_module', 'puissance_module')
    def _compute_puissance_total(self):
        for record in self:
            record.puissance_total = record.puissance_module * record.nombre_module / 1000

    onduleur_pv_1 = fields.Many2one('onduleur.pv', string='Référence Onduleur PV 1')
    marque_onduleur_1 = fields.Char(related='onduleur_pv_1.marque', string='Marque Onduleur PV 1')
    puissance_onduleur_1 = fields.Integer(related='onduleur_pv_1.puissance', string='Puissance onduleur 1 (kVA)')
    courant_sortie_1 = fields.Integer(related='onduleur_pv_1.courant_sortie',
                                      string='Calibre Disjoncteur Onduleur 1 (A)')
    nombre_onduleur_1 = fields.Integer(string='Nombre d’onduleur 1')

    onduleur_pv_2 = fields.Many2one('onduleur.pv', string='Référence Onduleur PV 2')
    marque_onduleur_2 = fields.Char(related='onduleur_pv_2.marque', string='Marque Onduleur PV 2')
    puissance_onduleur_2 = fields.Integer(related='onduleur_pv_2.puissance', string='Puissance onduleur 2 (kVA)')
    courant_sortie_2 = fields.Integer(related='onduleur_pv_2.courant_sortie',
                                      string='Calibre Disjoncteur Onduleur 2 (A)')
    nombre_onduleur_2 = fields.Integer(string='Nombre d’onduleur 2')

    puissance_total_ac = fields.Integer(string='Puissance Total AC (kVA)', compute="_compute_puissance_total_ac")

    @api.depends('puissance_onduleur_1', 'nombre_onduleur_1', 'puissance_onduleur_2', 'nombre_onduleur_2')
    def _compute_puissance_total_ac(self):
        for record in self:
            record.puissance_total_ac = record.puissance_onduleur_1 * record.nombre_onduleur_1 + record.puissance_onduleur_2 * record.nombre_onduleur_2

    courant_sortie_total = fields.Integer(string='Courant de sortie Total AC (A)',
                                          compute="_compute_courant_sortie_total")

    @api.depends('courant_sortie_1', 'nombre_onduleur_1', 'courant_sortie_2', 'nombre_onduleur_2')
    def _compute_courant_sortie_total(self):
        for record in self:
            record.courant_sortie_total = record.courant_sortie_1 * record.nombre_onduleur_1 + record.courant_sortie_2 * record.nombre_onduleur_2

    state_onduleur = fields.Selection([
        ('ras', 'RAS'),
        ('danger', 'A régulariser')],
        compute="_compute_state_onduleur", string="Statut")

    @api.depends('courant_sortie_total', 'puissance_disj_steg')
    def _compute_state_onduleur(self):
        for record in self:
            if record.courant_sortie_total <= record.puissance_disj_steg:
                record.state_onduleur = "ras"
            else:
                record.state_onduleur = "danger"

    note_info = fields.Text(string="Note")

    # page Prédimensionnement

    charge_etude = fields.Many2one('crm.commercial', string="Chargé d'étude",
                                   domain="[('charge_etude_user', '=', True)]")
    deadline = fields.Date(string="Deadline")
    statut_predimension = fields.Selection([
        ('1', 'En cours'),
        ('2', 'A vérifier'),
        ('3', 'A reprendre'),
        ('4', 'Validé'),
        ('5', 'Envoyé'),
    ], string="Statut")

    # page visite de site

    coordinateur = fields.Many2one('crm.commercial', string="Coordinateur Technique",
                                   domain="[('coordinateur_technique_user', '=', True)]", )
    date_visite = fields.Datetime(string="Date de visite de site")
    statut_visite_site = fields.Selection([
        ('1', 'Confirmée '),
        ('2', 'Reportée'),
        ('3', 'Effectuée'),
        ('4', 'Annulée'),
    ], string="Statut")

    # page chiffrage

    charge_chiffrage = fields.Many2one('crm.commercial', string="Chargé d'étude",
                                       domain="[('charge_etude_user', '=', True)]", )
    deadline_chiffrage = fields.Date(string="Deadline")
    statut_chiffrage = fields.Selection([
        ('1', 'En cours'),
        ('2', 'A vérifier'),
        ('3', 'A reprendre'),
        ('4', 'Validé'),
        ('5', 'Envoyé'),
    ], string="Statut")

    # page instructions

    date_depot = fields.Date(string="Date dépôt DA-DT STEG")
    statut_depot = fields.Selection([
        ('1', 'Approuvé'),
        ('2', 'Non approuvé'),
        ('3', 'Annule et Remplace')
    ], string="Statut")
    date_approbation = fields.Date(string="Date d'Approbation")
    date_depot_dr = fields.Date(string="Date Dépôt DR")
    date_reception_steg = fields.Date(string="Date Réception STEG")

    note_instructions = fields.Text(string="Note", domain="[('statut_depot', '=', 3]")
    credit_prosol = fields.Selection([
        ('1', '7 500'),
        ('2', '10 000'),
    ], string="Crédit Prosol",)

    # changement de stage CRM

    ordre_id = fields.Integer(string="Séquence", related="stage_id.ordre")
    next_ordre_id = fields.Integer(string="Séquence Suivante", compute="_compute_next_ordre_id")
    before_ordre_id = fields.Integer(string="Séquence Précédente", compute="_compute_before_ordre_id")

    def _compute_next_ordre_id(self):
        for ordre in self:
            ordre.next_ordre_id = ordre.ordre_id + 1

    def _compute_before_ordre_id(self):
        for ordre in self:
            ordre.before_ordre_id = ordre.ordre_id - 1

    def change_stage_with_before_ordre_id(self):
        for lead in self:
            before_stage = self.env['crm.stage'].search([('ordre', '=', lead.before_ordre_id)], limit=1)
            if before_stage:
                lead.stage_id = before_stage.id
                lead.create_stage_change_history()

    def change_stage_with_next_ordre_id(self):
        for lead in self:
            next_stage = self.env['crm.stage'].search([('ordre', '=', lead.next_ordre_id)], limit=1)
            if next_stage:
                lead.stage_id = next_stage.id
                lead.create_stage_change_history()

    # Historique stage

    stage_change_history_ids = fields.One2many('crm.stage.change.history', 'lead_id',
                                               string="Historique des changements de stage")

    @api.model
    def create(self, values):
        new_lead = super(CrmLead, self).create(values)
        new_lead.create_stage_change_history()
        return new_lead

    def create_stage_change_history(self):
        history_obj = self.env['crm.stage.change.history']
        for lead in self:
            new_history_vals = {
                'lead_id': lead.id,
                'stage_id': lead.stage_id.id,
            }

            # Vérifier si l'historique est vide ou si le dernier enregistrement est terminé
            if not lead.stage_change_history_ids or lead.stage_change_history_ids[-1].date_end:
                new_history_vals['date_start'] = fields.Datetime.now()

            # Mettre fin à l'enregistrement précédent (s'il est en cours)
            if lead.stage_change_history_ids and not lead.stage_change_history_ids[-1].date_end:
                lead.stage_change_history_ids[-1].end_stage()

            new_history = history_obj.create(new_history_vals)
            lead.write({'stage_change_history_ids': [(4, new_history.id)]})

        return True

    # technical fields to make page invisible

    page_info_projet = fields.Boolean(related='stage_id.page_info_projet', string="Afficher page Info Projet")
    page_predimension = fields.Boolean(related='stage_id.page_predimension', string="Afficher page Prédimensionnement")
    page_visite_site = fields.Boolean(related='stage_id.page_visite_site', string="Afficher page Visite de Site")
    page_chiffrage = fields.Boolean(related='stage_id.page_chiffrage', string="Afficher page Chiffrage")
    page_instructions = fields.Boolean(related='stage_id.page_instructions', string="Afficher page Instructions")
