import requests
import jwt
import datetime
from django.conf import settings
from requests.exceptions import JSONDecodeError 

class GetnetService:
    """
    Servicio para integración Web Checkout de Getnet (nueva API).
    """

    def __init__(self):
        self.api_base = settings.GETNET_BASE_URL_API
        self.checkout_base = settings.GETNET_BASE_URL_CHECKOUT
        self.login = settings.GETNET_LOGIN
        self.trankey = settings.GETNET_TRANKEY
        self.return_url = settings.GETNET_RETURN_URL
        self.notification_url = settings.GETNET_NOTIFICATION_URL
        
        # CORRECCIÓN 1: Importar la URL de consulta (ya definida en settings)
        self.api_create_request = settings.GETNET_API_CREATE_REQUEST
        self.api_query_request = settings.GETNET_API_QUERY_REQUEST


    # ------------------------------
    # Generar JWT de autenticación
    # ------------------------------
    def generate_jwt(self):
        now = datetime.datetime.utcnow()
        payload = {
            "iss": self.login,
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(minutes=5)).timestamp())
        }
        return jwt.encode(payload, self.trankey, algorithm="HS256")

    # ------------------------------
    # Crear transacción Web Checkout
    # ------------------------------
    def create_transaction(self, payment, student_email):
        buy_order = f"P{payment.id}-{datetime.datetime.now().strftime('%m%d%H%M%S')}"
        email = student_email or "no-email@example.com"

        payload = {
            "buy_order": buy_order,
            "amount": float(payment.amount),
            "currency": "CLP",
            "return_url": self.return_url,
            "notification_url": self.notification_url,
            "customer": {"email": email}
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.generate_jwt()}"
        }

        print("[Getnet] JWT:", self.generate_jwt())
        print("[Getnet] Payload:", payload)
        print("[Getnet] URL:", self.api_create_request)

        try:
            response = requests.post(
                self.api_create_request,
                json=payload,
                headers=headers,
                timeout=5
            )
            
            if not response.ok:
                print(f"[Getnet] ERROR HTTP {response.status_code}: {response.text}")
                
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", "Error desconocido del API")
                    return {"success": False, "error": f"API Error {response.status_code}: {error_message}"}
                except JSONDecodeError:
                    return {"success": False, "error": f"API Error {response.status_code}. Respuesta: {response.text}"}

            # Si la respuesta es 2xx, procede
            data = response.json()
            print("[Getnet] Respuesta completa:", data)

            # Obtener token de sesión real
            session_token = data.get("session_token") or data.get("session", {}).get("request_token")
            if not session_token:
                return {"success": False, "error": data.get("message", "Getnet no devolvió token.")}

            return {
                "success": True,
                "redirect_url": f"{self.checkout_base}/webcheckout?token={session_token}",
                "request_token": session_token,
                "buy_order": buy_order
            }

        except Exception as e:
            print(f"[Getnet] Error creando transacción (Conexión/Timeout): {e}")
            return {"success": False, "error": "Falla de comunicación con Getnet (Conexión/Timeout)."}


    # ------------------------------
    # Consultar estado de la transacción
    # ------------------------------
    def query_transaction_status(self, buy_order): 
        # La 'buy_order' es la 'reference' en este endpoint de consulta
        url = f"{self.api_query_request}/{buy_order}" 
        
        print("[Getnet] URL Consulta:", url) # DEBUG

        headers = {"Authorization": f"Bearer {self.generate_jwt()}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status() # Lanza excepción para códigos de error (4xx/5xx)
            
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"[Getnet] Error HTTP consultando estado ({err.response.status_code}): {err}")
            return {"error": f"Error HTTP {err.response.status_code} al consultar estado."}
        except Exception as e:
            print(f"[Getnet] Error consultando estado (Conexión/Timeout): {e}")
            return {"error": "No se pudo consultar el estado (Conexión/Timeout)."}