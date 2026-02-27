import asyncio
import concurrent.futures
import logging

from semantic_kernel.functions import kernel_function

from ..cosmos_service import get_cosmos_service

logger = logging.getLogger(__name__)


def run_async_sync(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, need to use a different approach
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        return asyncio.run(coro)


class ProductPlugin:
    """Enhanced plugin for product search and lookup using Cosmos DB"""

    @kernel_function(
        description="Lookup a product by ID and return natural language description"
    )
    def get_by_id(self, product_id: str) -> str:
        """Get product by ID with natural language response"""
        try:
            cosmos_service = get_cosmos_service()
            product = run_async_sync(cosmos_service.get_product_by_sku(product_id))
            if not product:
                return f"No encontré un servicio con ID '{product_id}'. ¿Puedes verificar el ID o buscar en nuestro catálogo?"

            # Format as natural language response using Product object attributes
            response = f"**{product.title}**"
            if product.price and product.price > 0:
                response += f" - ${product.price}"
            elif getattr(product, 'is_service', False):
                response += " - Solicitar cotización"
            if product.description:
                desc = product.description
                if len(desc) > 150:
                    desc = desc[:150] + "..."
                response += f"\n\n{desc}"
            if product.category:
                response += f"\n\nCategoría: {product.category}"
            if product.in_stock:
                response += "\n\n✅ Disponible"
            else:
                response += "\n\n❌ No disponible actualmente"

            return response

        except Exception as e:
            logger.error(f"Error getting product by ID {product_id}: {e}")
            return "Tengo problemas para consultar ese servicio. Por favor intenta de nuevo o contacta a soporte."

    @kernel_function(
        description="Search products with hybrid AI Search + Cosmos DB for maximum speed and accuracy"
    )
    def search(self, query: str, limit: int = 5) -> str:
        """Hybrid product search with AI Search first, then Cosmos DB fallback"""
        try:
            cosmos_service = get_cosmos_service()

            # Use hybrid search for best performance and accuracy
            products = run_async_sync(
                cosmos_service.search_products_hybrid(query, limit)
            )

            if not products:
                suggestions = self._get_search_suggestions(query)
                return f"No encontré servicios que coincidan con '{query}'. {suggestions}"

            response_parts = []

            if len(products) == 1:
                product = products[0]
                response_parts.append(
                    f"Encontré una coincidencia perfecta: **{product.title}**"
                )
                if product.price and product.price > 0:
                    response_parts.append(
                        f"Este servicio de {product.category} tiene un precio de ${product.price}"
                    )
                elif getattr(product, 'is_service', False):
                    response_parts.append("Solicitar cotización")
                if product.description:
                    desc = product.description
                    if len(desc) > 150:
                        desc = desc[:150] + "..."
                    response_parts.append(f"{desc}")
                if product.in_stock:
                    response_parts.append("✅ Disponible")
                else:
                    response_parts.append("❌ No disponible actualmente")
            else:
                response_parts.append(
                    f"Encontré {len(products)} servicios que coinciden con tu búsqueda:"
                )

                for i, product in enumerate(products[:3]):
                    product_dict = (
                        product.model_dump()
                        if hasattr(product, "model_dump")
                        else product
                    )
                    title = product_dict.get("title", "Servicio")
                    price = product_dict.get("price", 0)
                    category = product_dict.get("category", "")
                    is_service = product_dict.get("is_service", price == 0)
                    price_str = f"${price}" if price and price > 0 else "Cotizar"
                    response_parts.append(f"{i+1}. **{title}** - {price_str} ({category})")

                if len(products) > 3:
                    response_parts.append(
                        f"...y {len(products) - 3} servicios más disponibles."
                    )

            response_parts.append(
                "\n¿Te gustaría más información sobre algún servicio o necesitas ayuda con algo específico?"
            )

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error in hybrid product search with query '{query}': {e}")
            return "Tengo problemas para buscar servicios en este momento. Por favor intenta de nuevo o contacta a soporte."

    @kernel_function(description="Fast product search optimized for chat responses")
    def search_fast(self, query: str, limit: int = 3) -> str:
        """Ultra-fast product search using AI Search only"""
        try:
            cosmos_service = get_cosmos_service()

            # Use AI Search only for maximum speed
            products = run_async_sync(
                cosmos_service.search_products_ai_search(query, limit)
            )

            if not products:
                return f"No encontré servicios que coincidan con '{query}'. Prueba con otras palabras o explora nuestras categorías."

            if len(products) == 1:
                product = products[0]
                price_str = f"${product.price}" if product.price and product.price > 0 else "Cotizar"
                return f"**{product.title}** - {price_str} ({product.category})"
            else:
                response_parts = [f"Encontré {len(products)} servicios:"]
                for i, product in enumerate(products[:3]):
                    product_dict = (
                        product.model_dump()
                        if hasattr(product, "model_dump")
                        else product
                    )
                    title = product_dict.get("title", "Servicio")
                    price = product_dict.get("price", 0)
                    price_str = f"${price}" if price and price > 0 else "Cotizar"
                    response_parts.append(f"{i+1}. **{title}** - {price_str}")
                return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error in fast product search: {e}")
            return "Tengo problemas para buscar servicios. Por favor intenta de nuevo."

    def _get_search_suggestions(self, query: str) -> str:
        """Provide helpful search suggestions based on the query"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["seguridad", "ciberseguridad", "sec", "seg"]):
            return "Prueba buscando 'Ciberseguridad', 'SEC' o 'Seguridad Integral'."
        elif any(word in query_lower for word in ["it", "itsm", "gestión"]):
            return "Prueba buscando 'ITSM' o 'Gestión IT'."
        elif any(word in query_lower for word in ["ia", "inteligencia artificial", "artificial"]):
            return "Prueba buscando 'Inteligencia Artificial' o 'IA'."
        elif any(word in query_lower for word in ["cloud", "azure", "csp", "datos"]):
            return "Prueba buscando 'CSP', 'Cloud and Data' o 'Cloud'."
        else:
            return "Prueba buscando por categoría: Ciberseguridad, ITSM, IA, BRE, CSP, Cloud and Data, Servicios Administrados, Seguridad."

    @kernel_function(
        description="Get products by category with natural language responses"
    )
    def get_by_category(self, category: str, limit: int = 5) -> str:
        """Get products by category with natural language response"""
        try:
            cosmos_service = get_cosmos_service()
            products = run_async_sync(
                cosmos_service.get_products_by_category(category, limit)
            )

            if not products:
                return f"No encontré servicios en la categoría '{category}'. Prueba otras categorías o busca servicios específicos."

            response_parts = [f"Aquí están nuestros servicios de {category}:"]

            for i, product in enumerate(products[:5]):
                product_dict = (
                    product.model_dump() if hasattr(product, "model_dump") else product
                )
                title = product_dict.get("title", "Servicio")
                price = product_dict.get("price", 0)
                price_str = f"${price}" if price and price > 0 else "Cotizar"
                response_parts.append(f"{i+1}. **{title}** - {price_str}")

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error getting products by category '{category}': {e}")
            return f"Tengo problemas para consultar la categoría {category}. Por favor intenta de nuevo."

    @kernel_function(
        description="Get all available products with natural language response"
    )
    def get_all_products(self, limit: int = 10) -> str:
        """Get all products with natural language response"""
        try:
            cosmos_service = get_cosmos_service()
            products = run_async_sync(cosmos_service.get_products({"limit": limit}))

            if not products:
                return "No tengo servicios disponibles en este momento. Por favor contacta a soporte."

            response_parts = [
                f"Ofrecemos {len(products)} servicios en diferentes categorías:"
            ]

            categories = {}
            for product in products:
                category = product.category if product.category else "Otros"
                if category not in categories:
                    categories[category] = []
                categories[category].append(product)

            for category, cat_products in list(categories.items())[:3]:
                response_parts.append(f"\n**{category}:**")
                for product in cat_products[:2]:
                    title = product.title if hasattr(product, "title") else "Servicio"
                    price = product.price if hasattr(product, "price") else 0
                    price_str = f"${price}" if price and price > 0 else "Cotizar"
                    response_parts.append(f"- {title} ({price_str})")

            if len(categories) > 3:
                response_parts.append(
                    f"\n...y {len(categories) - 3} categorías más disponibles."
                )

            response_parts.append(
                "\n¿Te gustaría explorar una categoría específica o buscar algo en particular?"
            )

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error getting all products: {e}")
            return "Tengo problemas para acceder al catálogo de servicios. Por favor intenta de nuevo o contacta a soporte."
