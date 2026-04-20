"""
OpenClaw Contacts Chat Tool
MCP Tool para gestionar contactos desde el chat de OpenClaw
Permite crear, leer, actualizar y eliminar contactos en lenguaje natural
"""

import anthropic
import json
from typing import Optional


# Definición de herramientas MCP para contactos
CONTACTS_TOOLS = [
    {
        "name": "create_contact",
        "description": "Crear un nuevo contacto en Odoo",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre del contacto (requerido)"
                },
                "email": {
                    "type": "string",
                    "description": "Correo electrónico (opcional)"
                },
                "phone": {
                    "type": "string",
                    "description": "Teléfono (opcional)"
                },
                "company_name": {
                    "type": "string",
                    "description": "Nombre de la empresa si es contacto empresarial (opcional)"
                },
                "country": {
                    "type": "string",
                    "description": "País del contacto (opcional)"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_contact",
        "description": "Actualizar información de un contacto existente",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "integer",
                    "description": "ID del contacto a actualizar"
                },
                "name": {
                    "type": "string",
                    "description": "Nuevo nombre (opcional)"
                },
                "email": {
                    "type": "string",
                    "description": "Nuevo correo electrónico (opcional)"
                },
                "phone": {
                    "type": "string",
                    "description": "Nuevo teléfono (opcional)"
                },
                "country": {
                    "type": "string",
                    "description": "Nuevo país (opcional)"
                }
            },
            "required": ["contact_id"]
        }
    },
    {
        "name": "delete_contact",
        "description": "Eliminar un contacto de Odoo",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "integer",
                    "description": "ID del contacto a eliminar"
                }
            },
            "required": ["contact_id"]
        }
    },
    {
        "name": "get_contact",
        "description": "Obtener detalles completos de un contacto",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "integer",
                    "description": "ID del contacto"
                }
            },
            "required": ["contact_id"]
        }
    },
    {
        "name": "search_contacts",
        "description": "Buscar contactos por nombre, email o teléfono",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar (nombre, email o teléfono)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (default: 20)"
                }
            }
        }
    }
]


class ContactsToolExecutor:
    """Ejecutor de herramientas de contactos para OpenClaw"""
    
    def __init__(self, odoo_rpc_url: str, odoo_db: str, odoo_user: str, odoo_password: str):
        """
        Inicializar ejecutor de contactos
        
        Args:
            odoo_rpc_url: URL del servidor Odoo (ej: http://localhost:8069)
            odoo_db: Nombre de la base de datos Odoo
            odoo_user: Usuario de Odoo
            odoo_password: Contraseña de Odoo
        """
        import xmlrpc.client
        
        self.url = odoo_rpc_url
        self.db = odoo_db
        self.user = odoo_user
        self.password = odoo_password
        
        # Conectar a Odoo
        common = xmlrpc.client.ServerProxy(f"{odoo_rpc_url}/xmlrpc/2/common")
        self.uid = common.authenticate(odoo_db, odoo_user, odoo_password, {})
        self.models = xmlrpc.client.ServerProxy(f"{odoo_rpc_url}/xmlrpc/2/object")
    
    def create_contact(self, name: str, email: str = None, phone: str = None, 
                      company_name: str = None, country: str = None) -> dict:
        """Crear un nuevo contacto"""
        vals = {
            "name": name,
        }
        
        if email:
            vals["email"] = email
        if phone:
            vals["phone"] = phone
        if company_name:
            vals["is_company"] = True
        if country:
            vals["country_id"] = country
        
        try:
            contact_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "create", [vals]
            )
            
            return {
                "status": "success",
                "id": contact_id,
                "message": f"✅ Contacto '{name}' creado exitosamente (ID: {contact_id})"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error al crear contacto: {str(e)}"
            }
    
    def update_contact(self, contact_id: int, name: str = None, email: str = None,
                      phone: str = None, country: str = None) -> dict:
        """Actualizar un contacto"""
        vals = {}
        
        if name:
            vals["name"] = name
        if email:
            vals["email"] = email
        if phone:
            vals["phone"] = phone
        if country:
            vals["country_id"] = country
        
        if not vals:
            return {
                "status": "error",
                "message": "❌ Debes especificar al menos un campo para actualizar"
            }
        
        try:
            self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "write", [[contact_id], vals]
            )
            
            return {
                "status": "success",
                "id": contact_id,
                "message": f"✅ Contacto actualizado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error al actualizar contacto: {str(e)}"
            }
    
    def delete_contact(self, contact_id: int) -> dict:
        """Eliminar un contacto"""
        try:
            # Obtener nombre antes de eliminar
            contact_data = self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "read", [[contact_id], ["name"]]
            )
            
            contact_name = contact_data[0]["name"] if contact_data else "Desconocido"
            
            # Eliminar
            self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "unlink", [[contact_id]]
            )
            
            return {
                "status": "success",
                "message": f"✅ Contacto '{contact_name}' eliminado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error al eliminar contacto: {str(e)}"
            }
    
    def get_contact(self, contact_id: int) -> dict:
        """Obtener detalles de un contacto"""
        try:
            contact_data = self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "read", [
                    [contact_id],
                    ["name", "email", "phone", "is_company", "country_id", "city"]
                ]
            )
            
            if not contact_data:
                return {
                    "status": "error",
                    "message": f"❌ Contacto con ID {contact_id} no encontrado"
                }
            
            contact = contact_data[0]
            return {
                "status": "success",
                "contact": {
                    "id": contact_id,
                    "name": contact.get("name"),
                    "email": contact.get("email", ""),
                    "phone": contact.get("phone", ""),
                    "is_company": contact.get("is_company", False),
                    "country": contact.get("country_id", [""])[0] if contact.get("country_id") else "",
                    "city": contact.get("city", "")
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error al obtener contacto: {str(e)}"
            }
    
    def search_contacts(self, query: str = None, limit: int = 20) -> dict:
        """Buscar contactos"""
        try:
            domain = []
            if query:
                domain = [
                    "|", "|",
                    ("name", "ilike", query),
                    ("email", "ilike", query),
                    ("phone", "ilike", query)
                ]
            
            contact_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "search", [domain, ["limit", limit]]
            )
            
            if not contact_ids:
                return {
                    "status": "success",
                    "message": "No se encontraron contactos",
                    "contacts": []
                }
            
            contacts_data = self.models.execute_kw(
                self.db, self.uid, self.password,
                "res.partner", "read", [
                    contact_ids,
                    ["id", "name", "email", "phone", "is_company"]
                ]
            )
            
            return {
                "status": "success",
                "total": len(contacts_data),
                "contacts": contacts_data,
                "message": f"✅ Se encontraron {len(contacts_data)} contactos"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error al buscar contactos: {str(e)}"
            }
    
    def execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Ejecutar una herramienta de contactos"""
        if tool_name == "create_contact":
            return self.create_contact(
                tool_input["name"],
                tool_input.get("email"),
                tool_input.get("phone"),
                tool_input.get("company_name"),
                tool_input.get("country")
            )
        elif tool_name == "update_contact":
            return self.update_contact(
                tool_input["contact_id"],
                tool_input.get("name"),
                tool_input.get("email"),
                tool_input.get("phone"),
                tool_input.get("country")
            )
        elif tool_name == "delete_contact":
            return self.delete_contact(tool_input["contact_id"])
        elif tool_name == "get_contact":
            return self.get_contact(tool_input["contact_id"])
        elif tool_name == "search_contacts":
            return self.search_contacts(
                tool_input.get("query"),
                tool_input.get("limit", 20)
            )
        else:
            return {"status": "error", "message": f"Herramienta desconocida: {tool_name}"}


def run_contacts_chat(user_message: str, odoo_rpc_url: str, odoo_db: str, 
                     odoo_user: str, odoo_password: str) -> str:
    """
    Ejecutar un mensaje de chat con gestión de contactos
    
    Ejemplos de mensajes:
    - "Crear un contacto llamado Juan García con email juan@example.com"
    - "Buscar todos los contactos que contengan 'García'"
    - "Actualizar el contacto 123 con teléfono +34 123 456 789"
    - "Eliminar el contacto 456"
    - "Mostrar los detalles del contacto 789"
    """
    
    client = anthropic.Anthropic()  # Usa ANTHROPIC_API_KEY env var
    executor = ContactsToolExecutor(odoo_rpc_url, odoo_db, odoo_user, odoo_password)
    
    messages = [
        {
            "role": "user",
            "content": user_message
        }
    ]
    
    # Primera llamada a Claude con herramientas disponibles
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=CONTACTS_TOOLS,
        messages=messages
    )
    
    # Procesar tool calls
    while response.stop_reason == "tool_use":
        tool_use = next(
            (block for block in response.content if block.type == "tool_use"),
            None
        )
        
        if not tool_use:
            break
        
        tool_result = executor.execute_tool(tool_use.name, tool_use.input)
        
        # Continuar conversación con resultado
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(tool_result)
                }
            ]
        })
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            tools=CONTACTS_TOOLS,
            messages=messages
        )
    
    # Extraer respuesta final
    final_response = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "No se pudo procesar la solicitud"
    )
    
    return final_response


# Ejemplo de uso
if __name__ == "__main__":
    import os
    
    # Configuración desde variables de entorno
    ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
    ODOO_DB = os.getenv("ODOO_DB", "odoo")
    ODOO_USER = os.getenv("ODOO_USER", "admin")
    ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")
    
    # Ejemplos de uso
    test_messages = [
        "Crear un contacto llamado 'Juan García' con email juan@example.com y teléfono +34 123 456 789",
        "Buscar contactos que contengan 'García'",
        "Mostrar detalles del contacto 1",
    ]
    
    for message in test_messages:
        print(f"\n👤 Usuario: {message}")
        result = run_contacts_chat(message, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
        print(f"🤖 Assistant: {result}")
