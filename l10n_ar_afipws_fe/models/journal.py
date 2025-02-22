##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
import logging
from odoo.exceptions import UserError
#from odoo.addons.l10n_ar.models import account_journal

_logger = logging.getLogger(__name__)

#old_selection = account_journal.AccountJournal._point_of_sale_types_selection
#new_selection = old_selection.append(('electronic', 'Electronic'))
#account_journal.AccountJournal._point_of_sale_types_selection = new_selection


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    sequences = fields.One2many(comodel_name='ir.sequence',inverse_name='journal_id',string='Secuencias')
    _afip_ws_selection = (
        lambda self, *args, **kwargs: self._get_afip_ws_selection(
            *args, **kwargs))

    @api.model
    def _get_afip_ws_selection(self):
        return [
            ('wsfe', 'Mercado interno -sin detalle- RG2485 (WSFEv1)'),
            ('wsmtxca', 'Mercado interno -con detalle- RG2904 (WSMTXCA)'),
            ('wsfex', 'Exportación -con detalle- RG2758 (WSFEXv1)'),
            ('wsbfe', 'Bono Fiscal -con detalle- RG2557 (WSBFE)'),
            ('wsct', 'Factura Electrónica Comprobantes de Turismo'),
        ]

    afip_ws = fields.Selection(
        _afip_ws_selection,
        'AFIP WS',
    )

    def get_name_and_code_suffix(self):
        name = super(AccountJournal, self).get_name_and_code_suffix()
        if self.afip_ws == 'wsfex':
            name += ' Exportación'
        return name

    @api.model
    def create(self, vals):
        journal = super(AccountJournal, self).create(vals)
        if journal.l10n_ar_afip_pos_system == 'RLI_RLM' and journal.afip_ws:
            try:
                journal.sync_document_local_remote_number()
            except Exception:
                _logger.info(
                    'Could not sincronize local and remote numbers')
        return journal

    # @api.model
    # def _get_point_of_sale_types(self):
    #     types = super(AccountJournal, self)._get_point_of_sale_types()
    #     types.append(['electronic', _('Electronic')])
    #     return types

    @api.constrains('point_of_sale_type', 'afip_ws')
    def check_afip_ws_and_type(self):
        for rec in self:
            if rec.l10n_ar_afip_pos_system != 'RLI_RLM' and rec.afip_ws:
                raise UserError(_(
                    'You can only use an AFIP WS if type is "Electronic"'))

    def get_journal_letter(self, counterpart_partner=False):
        """Function to be inherited by afip ws fe"""
        letters = super(AccountJournal, self).get_journal_letter(
            counterpart_partner=counterpart_partner)
        # filter only for sales journals

        if self.type != 'sale':
            return letters
        if self.afip_ws == 'wsfe':
            letters = letters.filtered(
                lambda r: r.name != 'E')
        elif self.afip_ws == 'wsfex':
            letters = letters.filtered(
                lambda r: r.name == 'E')
        return letters

    def sync_document_local_remote_number(self):
        if self.type != 'sale':
            return True
        for journal_document_type in self.journal_document_type_ids:
            next_by_ws = int(
                journal_document_type.get_pyafipws_last_invoice(
                )['result']) + 1
            journal_document_type.sequence_id.number_next_actual = next_by_ws

    def check_document_local_remote_number(self):
        msg = ''
        if self.type != 'sale':
            return True
        #for journal_document_type in self.journal_document_type_ids:
        for sequence in self.l10n_ar_sequence_ids:
            journal_document_type = sequence.l10n_latam_document_type_id
            result = journal_document_type.get_pyafipws_last_invoice(None,journal_document_type,self,sequence)
            next_by_ws = int(result['result']) + 1
            next_by_seq = sequence.number_next_actual
            if next_by_ws != next_by_seq:
                msg += _(
                    '* Document Type %s, Local %i, Remote %i\n' % (
                        journal_document_type.name,
                        next_by_seq,
                        next_by_ws))
        if msg:
            msg = _('There are some doument desynchronized:\n') + msg
            raise UserError(msg)
        else:
            raise UserError(_('All documents are synchronized'))

    def test_pyafipws_dummy(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        self.ensure_one()
        if self.l10n_ar_afip_pos_system != 'FEERCEL':
            afip_ws = self.afip_ws
        else:
            afip_ws = 'wsfex'
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        ws.Dummy()
        title = _("AFIP service %s\n") % afip_ws
        msg = (
            "AppServerStatus: %s DbServerStatus: %s AuthServerStatus: %s" % (
                ws.AppServerStatus,
                ws.DbServerStatus,
                ws.AuthServerStatus))
        raise UserError(title + msg)

    def test_pyafipws_taxes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        ret = ws.ParamGetTiposTributos(sep="")
        msg = (_(" %s %s") % (
            '. '.join(ret), " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        title = _('Tributos en AFIP\n')
        raise UserError(title + msg)


    def test_pyafipws_point_of_sales(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == 'wsfex':
            ret = ws.GetParamPtosVenta()
        elif afip_ws == 'wsfe':
            ret = ws.ParamGetPtosVenta(sep=" ")
        # elif afip_ws == 'wsct':
        #     ret = ws.ConsultarPuntosVenta() 
        # wsct queda comentado porque pincha
        else:
            raise UserError(_(
                'Get point of sale for ws %s is not implemented yet') % (
                afip_ws))
        msg = (_(" %s %s") % (
            '. '.join(ret), " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        title = _('Enabled Point Of Sales on AFIP\n')
        raise UserError(title + msg)

    def get_pyafipws_cuit_document_classes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == 'wsfex':
            ret = ws.GetParamTipoCbte(sep=",")
        elif afip_ws == 'wsfe':
            ret = ws.ParamGetTiposCbte(sep=",")
        elif afip_ws == 'wsbfe':
            ret = ws.GetParamTipoCbte()
        elif afip_ws == 'wsct':
            ret = ws.ConsultarTiposComprobante()
        else:
            raise UserError(_(
                'Get document types for ws %s is not implemented yet') % (
                afip_ws))
        msg = (_(
            "Authorized Document Clases on AFIP\n%s\n. \nObservations: %s") % (
            '\n '.join(ret), ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        raise UserError(msg)

    def get_pyafipws_zonas(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == 'wsbfe':
            ret = ws.GetParamZonas()
        else:
            raise UserError(_(
                'Get zonas for ws %s is not implemented yet') % (
                afip_ws))
        msg = (_(
            "Zonas on AFIP\n%s\n. \nObservations: %s") % (
            '\n '.join(ret), ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        raise UserError(msg)

    def get_pyafipws_NCM(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == 'wsbfe':
            ret = ws.GetParamNCM()
        else:
            raise UserError(_(
                'Get NCM for ws %s is not implemented yet') % (
                afip_ws))
        msg = (_(
            "Zonas on AFIP\n%s\n. \nObservations: %s") % (
            '\n '.join(ret), ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        raise UserError(msg)

    def get_pyafipws_currencies(self):
        self.ensure_one()
        return self.env['res.currency'].get_pyafipws_currencies(
            afip_ws=self.afip_ws, company=self.company_id)

    def action_get_connection(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        self.company_id.get_connection(afip_ws).connect()

    def get_pyafipws_currency_rate(self, currency):
        raise UserError(currency.get_pyafipws_currency_rate(
            afip_ws=self.afip_ws,
            company=self.company_id,
        )[1])
