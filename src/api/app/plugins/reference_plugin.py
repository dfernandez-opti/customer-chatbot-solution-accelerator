import logging

from semantic_kernel.functions import kernel_function

from ..config import has_azure_search_config
from ..services.search import search_reference_enhanced

logger = logging.getLogger(__name__)


class ReferencePlugin:
    """Enhanced plugin for reference document lookup using Azure Search"""

    def __init__(self):
        self.is_configured = has_azure_search_config()

    @kernel_function(
        description="Search reference documents for policy and support information with natural language responses"
    )
    def lookup(self, query: str, top: int = 3) -> str:
        """Enhanced lookup with natural language responses"""
        if not self.is_configured:
            return "No tengo acceso a la información de políticas en este momento. Por favor contacta a nuestro equipo de soporte."

        try:
            hits = search_reference_enhanced(query, top)

            if not hits:
                return "No encontré información específica sobre eso. ¿Te gustaría que te pongamos en contacto con nuestro equipo de soporte?"

            # Format response naturally using the best available information
            response_parts = []

            for hit in hits:
                # Prefer extracted answers if available
                if hit.get("answers"):
                    for answer in hit["answers"]:
                        response_parts.append(answer)
                else:
                    # Use content with smart truncation
                    content = hit["content"]
                    if len(content) > 200:
                        # Try to find a good break point
                        break_point = content.find(".", 150)
                        if break_point > 0:
                            content = content[: break_point + 1]
                        else:
                            content = content[:200] + "..."
                    response_parts.append(content)

            # Combine the best parts and limit length
            combined_response = " ".join(
                response_parts[:2]
            )  # Limit to 2 most relevant parts

            # Add helpful context if it's about returns or policies
            if any(
                keyword in query.lower()
                for keyword in ["return", "refund", "policy", "warranty", "devolución", "reembolso", "política", "garantía"]
            ):
                combined_response += " Si necesitas más ayuda, contacta a nuestro equipo de soporte."

            return combined_response

        except Exception as e:
            logger.error(f"Error searching reference documents: {e}")
            return "Tengo problemas para acceder a la información de políticas. Por favor contacta a nuestro equipo de soporte."

    @kernel_function(description="Get return policy information with natural language")
    def get_return_policy(self) -> str:
        """Get return policy information with natural language response"""
        return self.lookup("return policy refund exchange", top=2)

    @kernel_function(description="Get shipping information with natural language")
    def get_shipping_info(self) -> str:
        """Get shipping information with natural language response"""
        return self.lookup("shipping delivery time cost", top=2)

    @kernel_function(description="Get warranty information with natural language")
    def get_warranty_info(self) -> str:
        """Get warranty information with natural language response"""
        return self.lookup("warranty guarantee coverage", top=2)

    @kernel_function(description="Lookup policy information with context awareness")
    def lookup_policy(self, query: str, context: str = "") -> str:
        """Enhanced policy lookup with context awareness"""
        if not self.is_configured:
            return "No tengo acceso a la información de políticas. Por favor contacta a soporte."

        try:
            search_query = f"{query} {context}".strip()
            hits = search_reference_enhanced(search_query, top=3)

            if not hits:
                return "No encontré información específica sobre eso. ¿Te gustaría contactar a soporte?"

            # Format response naturally
            response_parts = []
            for hit in hits:
                if hit.get("answers"):
                    # Use extracted answers if available
                    for answer in hit["answers"]:
                        response_parts.append(answer)
                else:
                    # Use content with highlighting
                    content = hit["content"]
                    if len(content) > 200:
                        content = content[:200] + "..."
                    response_parts.append(content)

            return " ".join(response_parts[:2])

        except Exception as e:
            logger.error(f"Policy lookup error: {e}")
            return "Tengo problemas para acceder a la información de políticas. Por favor contacta a soporte."
