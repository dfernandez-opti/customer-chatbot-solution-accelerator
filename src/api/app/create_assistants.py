#!/usr/bin/env python3
"""
Create Azure AI Foundry assistants programmatically
"""
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)


async def create_assistants():
    print("Creating assistants in Azure AI Foundry project...")

    try:
        from config import settings
        from foundry_client import get_foundry_client, init_foundry_client

        # Initialize Foundry client
        print("Initializing Foundry client...")
        await init_foundry_client()
        client = get_foundry_client()

        # Get OpenAI client
        print("Getting OpenAI client...")
        openai_client = await client.get_openai_client(  # type: ignore
            api_version=settings.azure_openai_api_version
        )

        # Define assistants to create
        assistants_to_create = [
            {
                "name": "Orchestrator Agent",
                "description": "Main orchestrator that routes customer inquiries to specialized agents for product searches, order tracking, and policy questions.",
                "instructions": """Eres el orquestador principal del servicio al cliente de OPTI - tecnologías que dan valor. Responde SIEMPRE en español.

1. Analiza las consultas y enrútalas al especialista adecuado
2. Atiende preguntas generales y saludos
3. Proporciona asistencia completa usando las herramientas disponibles
4. Mantén un tono profesional y amable

Tienes herramientas para: búsqueda de servicios, seguimiento de pedidos, políticas y FAQ.""",
                "model": "gpt-4o",
            },
            {
                "name": "Product Lookup Agent",
                "description": "Specialized agent for product searches, recommendations, and catalog inquiries.",
                "instructions": """Eres un especialista en servicios de OPTI. Responde SIEMPRE en español.

Tu expertise incluye: búsqueda de servicios (SEC, ITSM, IA, BRE, CSP, Cloud and Data, ADM, SEG), recomendaciones, cotizaciones, descripciones y categorías. Usa las herramientas de búsqueda para dar información precisa.""",
                "model": "gpt-4o",
            },
            {
                "name": "Order Status Agent",
                "description": "Specialized agent for order tracking, status updates, and order management.",
                "instructions": """Eres un especialista en pedidos de OPTI. Responde SIEMPRE en español. Ayudas con estado de pedidos, historial, reembolsos, envíos y modificaciones.""",
                "model": "gpt-4o",
            },
            {
                "name": "Knowledge Agent",
                "description": "Specialized agent for policies, FAQs, warranties, and general support information.",
                "instructions": """Eres un especialista en conocimiento de OPTI. Responde SIEMPRE en español. Proporcionas información sobre políticas de devolución, garantías, envíos, FAQs y procedimientos de la empresa.""",
                "model": "gpt-4o",
            },
        ]

        created_assistants = []

        for assistant_config in assistants_to_create:
            print(f"\nCreating {assistant_config['name']}...")

            try:
                # Create assistant
                assistant = await openai_client.beta.assistants.create(
                    name=assistant_config["name"],
                    description=assistant_config["description"],
                    instructions=assistant_config["instructions"],
                    model=assistant_config["model"],
                    tools=[],  # We'll add tools later through plugins
                )

                print(f"✅ Created {assistant.name}")
                print(f"   ID: {assistant.id}")
                print(f"   Model: {assistant.model}")

                created_assistants.append(
                    {
                        "name": assistant_config["name"],
                        "id": assistant.id,
                        "role": assistant_config["name"].lower().replace(" ", "_"),
                    }
                )

            except Exception as e:
                print(f"❌ Failed to create {assistant_config['name']}: {e}")

        # Print environment variable updates
        if created_assistants:
            print("\n🎯 Update your .env file with these new assistant IDs:")
            print("=" * 60)

            env_mapping = {
                "orchestrator_agent": "FOUNDRY_ORCHESTRATOR_AGENT_ID",
                "product_lookup_agent": "FOUNDRY_PRODUCT_AGENT_ID",
                "order_status_agent": "FOUNDRY_ORDER_AGENT_ID",
                "knowledge_agent": "FOUNDRY_KNOWLEDGE_AGENT_ID",
            }

            for assistant in created_assistants:
                role = assistant["role"]
                if role in env_mapping:
                    env_var = env_mapping[role]
                    print(f'{env_var}="{assistant["id"]}"')

            print("=" * 60)

        return created_assistants

    except Exception as e:
        print(f"❌ Failed to create assistants: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    asyncio.run(create_assistants())
