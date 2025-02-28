from odoo  import fields, api, models
from odoo.exceptions import UserError

class PaymentRequest(models.Model):
    _name = "payment.request"
    _description = "Payment Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # _rec_name="number"
    def _compute_number(self):
        for record in self:
            zeroes = "0"*(5 - len(str(record.id)))
            record.name = "PAY-RQ-"+str(record.create_date.year)+"/"+str(record.create_date.month)+"/"+zeroes+str(record.id)
    name=fields.Char(string="Number",compute="_compute_number")
    source_type = fields.Selection(selection=[('other','Other'),('advance','Advance'),('sfc','Student Faculty Club')],string="Source Type", required=True)
    sfc_source = fields.Char(string="SFC Source",readonly=True)
    source_user = fields.Many2one('res.users',string="Source User", default=lambda self: self.env.user, readonly=True)
    amount = fields.Monetary(string="Amount")
    payment_expect_date = fields.Date(string="Expected Date")
    payment_date = fields.Date(string="Date of Payment", readonly=True)
    def get_default_acc_manager(self):
        if self.env.user.has_group('openeducat_core.group_op_accounts'):
            return self.env.user.id
        else:
            return False
    def get_acc_head_domain(self):
        return [('id', 'in', self.env.ref('openeducat_core.group_op_accounts').users.ids)]
    def get_acc_domain(self):
        return [('id', 'in', self.env.ref('openeducat_core.group_op_accounts').users.ids)]
    accounting_head = fields.Many2one('res.users',string="Accounting Manager",domain=get_acc_head_domain, default=get_default_acc_manager)
    accountant = fields.Many2one('res.users', string="Accountant",readonly=True)
    # @api.multi
    # @api.onchange('source_type')
    # def onchange_company_id(self):
    #     users = self.env.ref('group_accounting_manager').users.ids
    #     return {'domain': {'accounting_head': [('id', 'in', users.ids)]}}
    company_id = fields.Many2one(
            'res.company', store=True, copy=False,
            string="Company",
            default=lambda self: self.env.user.company_id.id,
            readonly=True)
    currency_id = fields.Many2one(
            'res.currency', string="Currency",
            related='company_id.currency_id',
            default=lambda
            self: self.env.user.company_id.currency_id.id,
            readonly=True)

    state = fields.Selection(string="State",selection=[('draft','Draft'),('payment_request','Payment Requested'),('approved','Head Approved'),('payment_draft','Payment Drafted'),('paid','Paid'),('reject','Rejected')])
    description = fields.Text(string="Description")
    account_name = fields.Char(string="Account Name")
    account_no = fields.Char(string="Account No")
    ifsc_code = fields.Char(string="IFSC Code")
    bank_name = fields.Char(string="Bank Name")
    bank_branch = fields.Char(string="Bank Branch")
    payments = fields.One2many('account.payment','payment_request_id',string="Payments")
    def _compute_hide_register_pay_button(self):
        for record in self:
            record.hide_register_pay_button = (record.state in ('draft','paid','reject') ) or ( not record.is_account_head and (record.state not in ('payment_draft','approved')) )
    hide_register_pay_button = fields.Boolean(compute="_compute_hide_register_pay_button",default=True)

    def _compute_is_account_head(self):
        for record in self:
            record.is_account_head = self.env.user.has_group('openeducat_core.group_op_accounts')
    is_account_head = fields.Boolean(string="Is Accounting Head",compute="_compute_is_account_head")


    def _compute_payment_count(self):
        for record in self:
            record.payment_count = len(record.payments)
    payment_count = fields.Integer(string="Payments Count",compute="_compute_payment_count")
    
    @api.model
    def create(self, vals):
        vals['state'] = 'draft'
        result = super(PaymentRequest, self).create(vals)
        return result
    
    def action_confirm(self):
        if not self.accounting_head:
            raise UserError("An Accounting manager must be set before confirming a payment request!")
        elif not self.payment_expect_date:
            raise UserError("You have to set an expected payment date before confirming the request")
        else:
            # create new activity for the accounting manager to approve the pay request
            self.activity_schedule(
                'logic_payments_17.mail_activity_type_pay_request',
                user_id = self.accounting_head.id,
                payment_request = self.id,
                date_deadline=self.payment_expect_date,
                is_pay_approve_request=True,
                summary=f"Payment Request of {self.currency_id.symbol}{self.amount} from {self.env.user.name}"
            )
            self.accountant = self.env.user.id
            self.state = 'payment_request'

    def head_approve(self):
        # Retrieve the approval request activities
        activity_ids = self.env['mail.activity'].search([('payment_request', '=', self.id)], order='create_date asc')

        if activity_ids:
            activity_id = activity_ids[-1]  # Get the last activity
            activity_id.action_feedback(feedback='Approved')

        self.state = 'approved'

        # Create new activity for the accountant to register the payment
        # self.activity_schedule(
        #     'logic_payments_17.mail_activity_type_pay_request',
        #     user_id = self.accountant.id,
        #     payment_request = self.id,
        #     date_deadline=self.payment_expect_date,
        #     is_pay_approve_request=False,
        #     summary=f"Register Payment of {self.currency_id.symbol}{self.amount}"
        # )

    def register_payment(self):
        # Display a popup with the entered details
        if self.sfc_source:
            partner_type = 'sfc'
        else:
            partner_type = False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Payment',
            'res_model': 'payment.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'amount': self.amount,'payment_request_id':self.id ,'partner_type':partner_type}
        }
    def reject_payment(self):
        if self.state=='approved' and not self.env.user.has_group('openeducat_core.group_op_accounts'):
            raise UserError("Only an Accounting Manager can reject an approved payment request")
        else:
            # retrieve the last pay request activity and set it to rejected (and delete it)
            activity_ids = self.env['mail.activity'].search([('user_id','=',self.accountant.id),('payment_request','=',self.id)],order='create_date asc')
            if activity_ids:
                activity_id = activity_ids[-1]
                activity_id.action_feedback(feedback='Rejected')
                self.state = 'reject'
                self.sfc_source.write({
                    'state':'reject'
                })
            else:
                # if no approval request activity is present, create new activity and set it to rejected
                self.activity_schedule(
                    'logic_payments_17.mail_activity_type_pay_request',
                    user_id = self.env.user.id,
                    payment_request = self.id,
                    date_deadline=self.payment_expect_date,
                    is_pay_approve_request=True,
                    summary=f"Payment Request of {self.currency_id.symbol}{self.amount} from {self.accountant.name}"
                )
                activity_ids = self.env['mail.activity'].search([('user_id','=',self.env.user.id),('payment_request','=',self.id)],order='create_date asc')
                activity_id = activity_ids[-1]
                activity_id.action_feedback(feedback='Rejected')
        self.state = 'reject'
        if self.sfc_source:
            self.sfc_source.write({
                'state':'reject'
            })