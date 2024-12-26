# See LICENSE file for full copyright and licensing details.

# (TODO) ver si se puede parsear y modificar el resultado de super para devolver en ambos métodos

from odoo import models

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_journal_letter(self, counterpart_partner=False):
        if self.afip_ws == 'wsct':
            letters = ['T']
        else:
            letters = super()._get_journal_letter(counterpart_partner)
        
        return letters
    
    def _get_codes_per_journal_type(self, afip_pos_system):
        if self.afip_ws == 'wsct':
            codes = ['195']
            return [('code', 'in', codes)]
        codes = super()._get_codes_per_journal_type(afip_pos_system)
        return codes
    
            