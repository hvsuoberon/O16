# # -*- coding: utf-8 -*-
# 
# import json
# from lxml import etree
# from datetime import datetime
# from dateutil.relativedelta import relativedelta
# 
# from odoo import api, fields, models, _
# from odoo.tools import float_is_zero, float_compare
# from odoo.tools.misc import formatLang
# 
# from odoo.exceptions import UserError, RedirectWarning, ValidationError
# 
# import odoo.addons.decimal_precision as dp
# import logging
# 
# def _check_balance(self, p_id, acc_id, period_id, date, source_id):
# 
#     xcurbal = 0
#     if acc_id and p_id and period_id and date and source_id:
#         query = """
#                     SELECT 'APP' source, sum(budgeting_appropriationdet.amount) total 
#                         FROM budgeting_appropriation 
#                             inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id  
#                         WHERE budgeting_appropriation.state = 'approved' and budgeting_appropriation.partner_id = %s 
#                         AND budgeting_appropriationdet.account_id = %s and budgeting_appropriation.period_id = %s
#                         and budgeting_appropriation.date_approved <= %s
#                         and budgeting_appropriation.source_id <= %s
#                     union
#                     SELECT 'OBR' source, sum(budgeting_obrdet.amount) total 
#                         FROM budgeting_obr 
#                             inner join budgeting_obrdet on budgeting_obr.id = budgeting_obrdet.obr_id  
#                         WHERE budgeting_obr.state = 'approved' and budgeting_obr.partner_id = %s 
#                         AND budgeting_obrdet.account_id = %s and budgeting_obr.period_id = %s    
#                         and budgeting_obr.date_approved <= %s
#                         and budgeting_obr.source_id <= %s
#                     union    
#                     SELECT 'AUF' source, sum(budgeting_augmentationdetfrom.amount) total 
#                         FROM budgeting_augmentation 
#                             inner join budgeting_augmentationdetfrom on budgeting_augmentation.id = budgeting_augmentationdetfrom.aug_id  
#                         WHERE budgeting_augmentation.state = 'approved' and budgeting_augmentation.partner_id = %s 
#                         AND budgeting_augmentationdetfrom.account_id = %s and budgeting_augmentation.period_id = %s
#                         and budgeting_augmentation.date_approved <= %s
#                         and budgeting_augmentation.source_id <= %s
#                     union
#                     SELECT 'AUT' source, sum(budgeting_augmentationdetto.amount) total 
#                         FROM budgeting_augmentation 
#                             inner join budgeting_augmentationdetto on budgeting_augmentation.id = budgeting_augmentationdetto.aug_id  
#                         WHERE budgeting_augmentation.state = 'approved' and budgeting_augmentation.partner_id = %s 
#                         AND budgeting_augmentationdetto.account_id = %s and budgeting_augmentation.period_id = %s
#                         and budgeting_augmentation.date_approved <= %s
#                         and budgeting_augmentation.source_id <= %s
#                         ;
#                 """
#         self.env.cr.execute(query, (p_id, acc_id, period_id, date, source_id, p_id, acc_id, period_id, date, source_id,p_id, acc_id, period_id, date, source_id,p_id, acc_id, period_id, date, source_id))
#         query_results = self.env.cr.dictfetchall()
#         
#         for result in query_results:
#             if result['total']:
#                 if result['source'] in ('AUT','APP'):
#                     xcurbal = xcurbal + result['total']
#                 else:
#                     xcurbal = xcurbal - result['total']
#     
#     return xcurbal
# 
# def _check_balance_pr(self, p_id, acc_id, period_id, date, source_id):
#     xcurbal = 0
#     if acc_id and p_id and period_id and source_id:
#         query = """
#                     SELECT 'APP' source, sum(budgeting_appropriationdet.amount) total 
#                         FROM budgeting_appropriation 
#                             inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id  
#                         WHERE budgeting_appropriation.state = 'approved' and budgeting_appropriation.partner_id = %s 
#                         AND budgeting_appropriationdet.account_id = %s and budgeting_appropriation.period_id = %s
#                         and budgeting_appropriation.date_approved <= %s
#                         and budgeting_appropriation.source_id <= %s
#                     union
#                     SELECT 'PR' source, sum(budgeting_prdet.amount) total 
#                         FROM budgeting_pr 
#                             inner join budgeting_prdet on budgeting_pr.id = budgeting_prdet.pr_id  
#                         WHERE budgeting_pr.state in ('approved','obr') and budgeting_pr.partner_id = %s 
#                         AND budgeting_prdet.account_id = %s and budgeting_pr.period_id = %s   
#                         and budgeting_pr.date_approved <= %s
#                         and budgeting_pr.source_id <= %s
#                         and budgeting_pr.id not in (select pr_id from budgeting_obr 
#                                                 where date_approved <= %s and state = 'approved' and pr_id is not null)
#                     union  
#                     SELECT 'OBR' source, sum(budgeting_obrdet.amount) total 
#                         FROM budgeting_obr 
#                             inner join budgeting_obrdet on budgeting_obr.id = budgeting_obrdet.obr_id  
#                         WHERE budgeting_obr.state = 'approved' and budgeting_obr.partner_id = %s 
#                         AND budgeting_obrdet.account_id = %s and budgeting_obr.period_id = %s  
#                         and budgeting_obr.date_approved <= %s
#                         and budgeting_obr.source_id <= %s  
#                     union    
#                     SELECT 'AUF' source, sum(budgeting_augmentationdetfrom.amount) total 
#                         FROM budgeting_augmentation 
#                             inner join budgeting_augmentationdetfrom on budgeting_augmentation.id = budgeting_augmentationdetfrom.aug_id  
#                         WHERE budgeting_augmentation.state = 'approved' and budgeting_augmentation.partner_id = %s 
#                         AND budgeting_augmentationdetfrom.account_id = %s and budgeting_augmentation.period_id = %s
#                         and budgeting_augmentation.date_approved <= %s
#                         and budgeting_augmentation.source_id <= %s
#                     union
#                     SELECT 'AUT' source, sum(budgeting_augmentationdetto.amount) total 
#                         FROM budgeting_augmentation 
#                             inner join budgeting_augmentationdetto on budgeting_augmentation.id = budgeting_augmentationdetto.aug_id  
#                         WHERE budgeting_augmentation.state = 'approved' and budgeting_augmentation.partner_id = %s 
#                         AND budgeting_augmentationdetto.account_id = %s and budgeting_augmentation.period_id = %s
#                         and budgeting_augmentation.date_approved <= %s
#                         and budgeting_augmentation.source_id <= %s
#                         ;
#                 """
#         self.env.cr.execute(query, (p_id, acc_id, period_id, date, source_id, p_id, acc_id, period_id, date, source_id, date,p_id, acc_id, period_id, date, source_id,p_id, acc_id, period_id, date, source_id,p_id, acc_id, period_id, date, source_id))
#         query_results = self.env.cr.dictfetchall()
#         
#         for result in query_results:
#             if result['total']:
#                 if result['source'] in ('AUT','APP'):
#                     xcurbal = xcurbal + result['total']
#                 else:
#                     xcurbal = xcurbal - result['total']
#                         
#     return xcurbal