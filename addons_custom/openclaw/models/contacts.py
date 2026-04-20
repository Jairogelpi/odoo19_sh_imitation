"""
OpenClaw Contacts Manager
Addon para crear, leer, actualizar y eliminar contactos en Odoo.
Integrado con OpenClaw para control de permisos y auditoría.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extensión del modelo Partner (Contacto) con capacidades de auditoría OpenClaw"""
    
    _inherit = "res.partner"
    
    # Campos de auditoría OpenClaw
    openclaw_created_by = fields.Many2one(
        "res.users",
        string="Creado por OpenClaw",
        readonly=True,
        help="Usuario que creó este contacto a través de OpenClaw"
    )
    openclaw_last_modified_by = fields.Many2one(
        "res.users",
        string="Última modificación por OpenClaw",
        readonly=True,
        help="Usuario que modificó este contacto a través de OpenClaw"
    )
    openclaw_request_id = fields.Char(
        string="ID de Solicitud OpenClaw",
        readonly=True,
        help="Referencia al request de OpenClaw que creó/modificó este contacto"
    )


class OpenClawContactsManager(models.AbstractModel):
    """Gestor de contactos vía OpenClaw"""
    
    _name = "openclaw.contacts"
    _description = "OpenClaw Contacts Manager"
    
    @api.model
    def create_contact(self, name: str, email: str = None, phone: str = None, 
                      company_name: str = None, country: str = None, request_id: str = None, **kwargs):
        """
        Crear un nuevo contacto en Odoo
        
        Args:
            name: Nombre del contacto (requerido)
            email: Correo electrónico (opcional)
            phone: Teléfono (opcional)
            company_name: Nombre de la empresa (opcional)
            country: País (opcional)
            request_id: ID del request de OpenClaw (para auditoría)
            **kwargs: Campos adicionales de res.partner
        
        Returns:
            dict: Datos del contacto creado
        """
        
        try:
            # Validar datos requeridos
            if not name or not name.strip():
                raise ValidationError("El nombre del contacto es obligatorio")
            
            # Preparar datos
            vals = {
                "name": name.strip(),
                "openclaw_request_id": request_id,
                "openclaw_created_by": self.env.user.id,
            }
            
            # Agregar campos opcionales
            if email and email.strip():
                vals["email"] = email.strip().lower()
            
            if phone and phone.strip():
                vals["phone"] = phone.strip()
            
            # Si es empresa, marcar como tal
            if company_name:
                vals["is_company"] = True
                if not name.strip().endswith("Inc") and not name.strip().endswith("Ltd"):
                    vals["company_name"] = company_name
            
            # Buscar país por código o nombre
            if country:
                country_obj = self.env["res.country"].search([
                    "|",
                    ("code", "ilike", country),
                    ("name", "ilike", country)
                ], limit=1)
                if country_obj:
                    vals["country_id"] = country_obj.id
            
            # Agregar otros campos personalizados
            vals.update(kwargs)
            
            # Crear contacto
            partner = self.env["res.partner"].create(vals)
            
            _logger.info(
                f"✅ Contacto creado por OpenClaw: {partner.name} (ID: {partner.id}, Request: {request_id})"
            )
            
            return {
                "status": "success",
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "phone": partner.phone,
                "message": f"Contacto '{partner.name}' creado exitosamente"
            }
        
        except ValidationError as e:
            _logger.warning(f"❌ Error validación al crear contacto: {e}")
            raise
        except Exception as e:
            _logger.error(f"❌ Error al crear contacto: {e}")
            raise UserError(f"Error al crear contacto: {str(e)}")
    
    @api.model
    def update_contact(self, contact_id: int, name: str = None, email: str = None, 
                      phone: str = None, country: str = None, request_id: str = None, **kwargs):
        """
        Actualizar un contacto existente
        
        Args:
            contact_id: ID del contacto a actualizar
            name: Nuevo nombre (opcional)
            email: Nuevo correo (opcional)
            phone: Nuevo teléfono (opcional)
            country: Nuevo país (opcional)
            request_id: ID del request de OpenClaw (para auditoría)
            **kwargs: Otros campos a actualizar
        
        Returns:
            dict: Datos del contacto actualizado
        """
        
        try:
            # Buscar contacto
            partner = self.env["res.partner"].browse(contact_id)
            if not partner.exists():
                raise ValidationError(f"Contacto con ID {contact_id} no encontrado")
            
            # Preparar datos a actualizar
            vals = {
                "openclaw_last_modified_by": self.env.user.id,
                "openclaw_request_id": request_id,
            }
            
            # Actualizar campos si se proporcionan
            if name:
                vals["name"] = name.strip()
            
            if email is not None:
                vals["email"] = email.strip().lower() if email else False
            
            if phone is not None:
                vals["phone"] = phone.strip() if phone else False
            
            if country:
                country_obj = self.env["res.country"].search([
                    "|",
                    ("code", "ilike", country),
                    ("name", "ilike", country)
                ], limit=1)
                if country_obj:
                    vals["country_id"] = country_obj.id
            
            # Agregar otros campos
            vals.update(kwargs)
            
            # Actualizar
            partner.write(vals)
            
            _logger.info(
                f"✅ Contacto actualizado por OpenClaw: {partner.name} (ID: {partner.id}, Request: {request_id})"
            )
            
            return {
                "status": "success",
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "phone": partner.phone,
                "message": f"Contacto '{partner.name}' actualizado exitosamente"
            }
        
        except ValidationError as e:
            _logger.warning(f"❌ Error al actualizar contacto: {e}")
            raise
        except Exception as e:
            _logger.error(f"❌ Error al actualizar contacto: {e}")
            raise UserError(f"Error al actualizar contacto: {str(e)}")
    
    @api.model
    def delete_contact(self, contact_id: int, request_id: str = None):
        """
        Eliminar un contacto
        
        Args:
            contact_id: ID del contacto a eliminar
            request_id: ID del request de OpenClaw (para auditoría)
        
        Returns:
            dict: Confirmación de eliminación
        """
        
        try:
            # Buscar contacto
            partner = self.env["res.partner"].browse(contact_id)
            if not partner.exists():
                raise ValidationError(f"Contacto con ID {contact_id} no encontrado")
            
            contact_name = partner.name
            contact_id_val = partner.id
            
            # Verificar si tiene transacciones asociadas
            has_invoices = self.env["account.invoice"].search([
                ("partner_id", "=", contact_id_val)
            ], limit=1)
            
            if has_invoices:
                _logger.warning(
                    f"⚠️ Intento de eliminar contacto con facturas: {contact_name}"
                )
                raise UserError(
                    f"No se puede eliminar el contacto '{contact_name}' porque tiene facturas asociadas. "
                    "Considera archivarlo en su lugar."
                )
            
            # Eliminar contacto
            partner.unlink()
            
            _logger.info(
                f"✅ Contacto eliminado por OpenClaw: {contact_name} (Request: {request_id})"
            )
            
            return {
                "status": "success",
                "id": contact_id_val,
                "name": contact_name,
                "message": f"Contacto '{contact_name}' eliminado exitosamente"
            }
        
        except ValidationError as e:
            _logger.warning(f"❌ Error al eliminar contacto: {e}")
            raise
        except Exception as e:
            _logger.error(f"❌ Error al eliminar contacto: {e}")
            raise UserError(f"Error al eliminar contacto: {str(e)}")
    
    @api.model
    def get_contact(self, contact_id: int):
        """
        Obtener detalles de un contacto
        
        Args:
            contact_id: ID del contacto
        
        Returns:
            dict: Datos del contacto
        """
        
        try:
            partner = self.env["res.partner"].browse(contact_id)
            if not partner.exists():
                raise ValidationError(f"Contacto con ID {contact_id} no encontrado")
            
            return {
                "status": "success",
                "id": partner.id,
                "name": partner.name,
                "email": partner.email or "",
                "phone": partner.phone or "",
                "is_company": partner.is_company,
                "country": partner.country_id.name if partner.country_id else "",
                "city": partner.city or "",
                "created_at": partner.create_date.isoformat() if partner.create_date else "",
                "openclaw_created_by": partner.openclaw_created_by.name if partner.openclaw_created_by else "Manual",
            }
        
        except Exception as e:
            _logger.error(f"❌ Error al obtener contacto: {e}")
            raise UserError(f"Error al obtener contacto: {str(e)}")
    
    @api.model
    def search_contacts(self, query: str = None, limit: int = 20):
        """
        Buscar contactos por nombre, email o teléfono
        
        Args:
            query: Texto de búsqueda
            limit: Límite de resultados
        
        Returns:
            list: Lista de contactos encontrados
        """
        
        try:
            domain = []
            
            if query:
                domain = [
                    "|", "|",
                    ("name", "ilike", query),
                    ("email", "ilike", query),
                    ("phone", "ilike", query),
                ]
            
            partners = self.env["res.partner"].search(domain, limit=limit)
            
            contacts = []
            for partner in partners:
                contacts.append({
                    "id": partner.id,
                    "name": partner.name,
                    "email": partner.email or "",
                    "phone": partner.phone or "",
                    "is_company": partner.is_company,
                })
            
            return {
                "status": "success",
                "total": len(contacts),
                "contacts": contacts,
                "message": f"Se encontraron {len(contacts)} contactos"
            }
        
        except Exception as e:
            _logger.error(f"❌ Error al buscar contactos: {e}")
            raise UserError(f"Error al buscar contactos: {str(e)}")
