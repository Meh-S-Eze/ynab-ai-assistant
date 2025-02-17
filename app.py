import streamlit as st
import os
from datetime import datetime, timedelta
from ynab_api.client import YNABClient
from ai_chat.handler import ChatHandler
from utils.logger import setup_logger
import random
import traceback

# Set up logger
logger = setup_logger('main_app')
logger.info("Starting YNAB AI Assistant")

# Verify required secrets
required_secrets = [
    "YNAB_API_KEY",
    "YNAB_BUDGET_ID",
    "GITHUB_TOKEN",  # Required for GitHub Model Registry
    "GITHUB_MODEL",
    "GITHUB_FALLBACK_MODEL"
]
missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
if missing_secrets:
    error_msg = f"Missing required secrets: {', '.join(missing_secrets)}"
    logger.error(error_msg)
    st.error(error_msg)
    st.stop()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
    logger.debug("Initialized empty message history")
if 'current_persona' not in st.session_state:
    st.session_state.current_persona = 'cheerleader'
    logger.debug("Set default persona to cheerleader")
if 'current_budget_id' not in st.session_state:
    st.session_state.current_budget_id = st.secrets["YNAB_BUDGET_ID"]
    logger.debug(f"Set default budget ID: {st.session_state.current_budget_id}")

# App title and description
st.title("YNAB AI Assistant 💰")
st.markdown("Chat with your budget! Get insights, motivation, and maybe a few laughs 😊")

# Initialize YNAB client first to get budgets
try:
    logger.info("Initializing YNAB client")
    ynab_client = YNABClient(
        api_key=st.secrets["YNAB_API_KEY"]
    )
    
    # Cache budgets for 5 minutes
    @st.cache_data(ttl=300)
    def get_cached_budgets():
        logger.debug("Fetching budgets (cached)")
        return ynab_client.get_budgets()
    
    # Get available budgets
    logger.debug("Getting budgets from cache or API")
    budgets = get_cached_budgets()
    if not budgets:
        error_msg = "No budgets found in your YNAB account"
        logger.error(error_msg)
        st.error(error_msg)
        st.stop()
        
    budget_options = {budget['name']: budget['id'] for budget in budgets}
    logger.debug(f"Found {len(budget_options)} budgets")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        
        # Budget selector
        st.subheader("Select Budget")
        
        # Find default index for current budget
        try:
            default_index = list(budget_options.values()).index(st.session_state.current_budget_id)
        except ValueError:
            logger.warning(f"Current budget ID {st.session_state.current_budget_id} not found in available budgets")
            default_index = 0
            # Update session state with first available budget
            st.session_state.current_budget_id = list(budget_options.values())[0]
            logger.info(f"Defaulting to first available budget: {list(budget_options.keys())[0]}")
        
        # Show budget selector
        selected_budget_name = st.selectbox(
            "Choose your budget:",
            options=list(budget_options.keys()),
            index=default_index
        )
        
        # Update budget ID if changed
        new_budget_id = budget_options[selected_budget_name]
        if new_budget_id != st.session_state.current_budget_id:
            logger.info(f"Switching budget from {st.session_state.current_budget_id} to {new_budget_id}")
            st.session_state.current_budget_id = new_budget_id
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"🔄 Switching to budget: {selected_budget_name}"
            })
        
        # Persona selector
        st.subheader("Select Personality")
        selected_persona = st.radio(
            "Choose your budget buddy:",
            ["cheerleader", "roaster"],
            index=0 if st.session_state.current_persona == 'cheerleader' else 1
        )
        
        if selected_persona != st.session_state.current_persona:
            logger.info(f"Switching persona from {st.session_state.current_persona} to {selected_persona}")
            st.session_state.current_persona = selected_persona
            st.session_state.messages.append({
                "role": "assistant",
                "content": "🔄 Personality switch! Let's chat about your money in a different way!"
            })
    
    # Update YNAB client with selected budget
    ynab_client.budget_id = st.session_state.current_budget_id
    logger.debug(f"Set YNAB client budget ID to: {ynab_client.budget_id}")
    
    logger.info("Initializing chat handler")
    chat_handler = ChatHandler()  # No need to pass OpenAI key anymore
    chat_handler.switch_persona(st.session_state.current_persona)
    logger.info("Clients initialized successfully")
    
except Exception as e:
    error_msg = f"Error initializing clients: {str(e)}"
    logger.error(f"Stack trace:\n{traceback.format_exc()}")
    st.error(error_msg)
    st.stop()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask about your budget..."):
    logger.info(f"Received user input: {prompt}")
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    try:
        # Cache functions for budget data
        @st.cache_data(ttl=300)  # Cache for 5 minutes
        def get_cached_categories(budget_id):
            logger.debug("Fetching categories (cached)")
            return ynab_client.get_categories(budget_id)
            
        @st.cache_data(ttl=60)  # Cache for 1 minute
        def get_cached_transactions(budget_id, since_date):
            logger.debug("Fetching transactions (cached)")
            return ynab_client.get_transactions(budget_id, since_date)
            
        @st.cache_data(ttl=60)  # Cache for 1 minute
        def get_cached_month_summary(budget_id):
            logger.debug("Fetching month summary (cached)")
            return ynab_client.get_month_summary(budget_id)
        
        # Get recent context
        logger.debug("Gathering context for AI response")
        context = {}
        
        # Get budget info from already cached budgets
        logger.debug("Getting budget info from cache")
        current_budget = next((b for b in budgets if b['id'] == st.session_state.current_budget_id), None)
        if current_budget:
            context['budget_name'] = current_budget['name']
        else:
            logger.warning(f"Could not find budget with ID: {st.session_state.current_budget_id}")
        
        # Get categories and their status
        logger.debug("Getting categories from cache or API")
        categories = get_cached_categories(st.session_state.current_budget_id)
        if categories:
            # First, summarize by category group
            group_summary = []
            category_summary = []
            for group in categories:
                if not group['hidden'] and not group['deleted']:
                    group_total_budgeted = 0
                    group_total_activity = 0
                    group_categories = []
                    
                    for cat in group['categories']:
                        if not cat['hidden'] and not cat['deleted']:
                            cat_budgeted = ynab_client.milliunits_to_dollars(cat['budgeted'])
                            cat_activity = ynab_client.milliunits_to_dollars(cat['activity'])
                            group_total_budgeted += cat_budgeted
                            group_total_activity += cat_activity
                            
                            category_summary.append(
                                f"{cat['name']}: Budgeted ${cat_budgeted:.2f}, "
                                f"Activity ${cat_activity:.2f}, "
                                f"Balance ${ynab_client.milliunits_to_dollars(cat['balance']):.2f}"
                            )
                            group_categories.append(cat['name'])
                    
                    group_summary.append(
                        f"{group['name']}: Total Budgeted ${group_total_budgeted:.2f}, "
                        f"Total Activity ${group_total_activity:.2f}, "
                        f"Categories: {', '.join(group_categories)}"
                    )
            
            context['category_groups'] = "\n".join(group_summary)
            context['categories'] = "\n".join(category_summary)
        else:
            logger.info("No categories found")
        
        # Get recent transactions with income vs expense breakdown
        logger.debug("Fetching recent transactions")
        # TEMPORARY: Use 2024 for testing
        current_date = datetime.now().replace(year=2024)
        since_date = (current_date - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_txns = get_cached_transactions(st.session_state.current_budget_id, since_date)
        if recent_txns:
            # Calculate income vs expenses
            total_income = sum(
                ynab_client.milliunits_to_dollars(tx['amount']) 
                for tx in recent_txns if tx['amount'] > 0
            )
            total_expenses = abs(sum(
                ynab_client.milliunits_to_dollars(tx['amount']) 
                for tx in recent_txns if tx['amount'] < 0
            ))
            net_flow = total_income - total_expenses
            
            context['recent_transactions'] = (
                f"Last 7 days: Income ${total_income:.2f}, "
                f"Expenses ${total_expenses:.2f}, "
                f"Net ${net_flow:.2f}"
            )
            
            # Add detailed transaction list
            transaction_details = []
            for tx in recent_txns[:10]:  # Show last 10 transactions
                amount = ynab_client.milliunits_to_dollars(tx['amount'])
                transaction_details.append(
                    f"{tx['date']}: {tx.get('payee_name', 'Unknown')} - "
                    f"${abs(amount):.2f} ({'income' if amount > 0 else 'expense'})"
                )
            context['transaction_details'] = "\n".join(transaction_details)
        else:
            logger.info("No recent transactions found")
        
        # Get current month summary with to be budgeted
        logger.debug("Fetching month summary")
        month_summary = get_cached_month_summary(st.session_state.current_budget_id)
        if month_summary:
            to_be_budgeted = ynab_client.milliunits_to_dollars(month_summary.get('to_be_budgeted', 0))
            budgeted = ynab_client.milliunits_to_dollars(month_summary.get('budgeted', 0))
            activity = ynab_client.milliunits_to_dollars(month_summary.get('activity', 0))
            
            context['category_status'] = (
                f"To Be Budgeted: ${to_be_budgeted:.2f}, "
                f"Total Budgeted: ${budgeted:.2f}, "
                f"Total Activity: ${activity:.2f}"
            )
        else:
            logger.info("No month summary available")

        # Get AI response
        logger.info("Getting AI response")
        response = chat_handler.get_response(prompt, context)
        response = chat_handler.ensure_emoji(response)
        logger.debug(f"Got AI response: {response}")

        # Check if this is a categorization request
        if any(keyword in prompt.lower() for keyword in ['categorize', 'set category', 'move to category']):
            # Look for transaction and category in the prompt
            words = prompt.lower().split()
            try:
                # Find the transaction
                transaction = None
                for i in range(len(words)):
                    if len(words[i]) > 4:  # Only try with longer words to avoid noise
                        test_transaction = ynab_client.find_transaction_by_description(words[i])
                        if test_transaction:
                            transaction = test_transaction
                            break

                if not transaction:
                    response += "\n\nI couldn't find that transaction. Could you be more specific about which transaction you want to categorize?"
                else:
                    # Find the category
                    category = None
                    for i in range(len(words)):
                        if len(words[i]) > 4:  # Only try with longer words to avoid noise
                            test_category = ynab_client.find_category_by_name(words[i])
                            if test_category:
                                category = test_category
                                break

                    if not category:
                        response += f"\n\nI found the transaction for {transaction.get('payee_name')}, but I couldn't determine which category you want to use. Could you specify the category?"
                    else:
                        # Update the transaction
                        try:
                            updated = ynab_client.update_transaction(
                                transaction_id=transaction['id'],
                                category_id=category['id']
                            )
                            response += f"\n\nGreat! I've categorized the transaction '{transaction.get('payee_name')}' as '{category['name']}' 🎯"
                        except Exception as e:
                            response += f"\n\nI found both the transaction and category, but couldn't update it: {str(e)} 😅"
            except Exception as e:
                logger.error(f"Error processing categorization request: {str(e)}")
                response += "\n\nI had trouble processing that categorization request. Could you try rephrasing it?"

        # Add response to chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)

    except Exception as e:
        error_msg = f"Oops! Something went wrong: {str(e)} 😅"
        logger.error(f"Error processing request:\n{traceback.format_exc()}")
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        with st.chat_message("assistant"):
            st.write(error_msg)

# Fun footer
st.markdown("---")
footer_messages = [
    "Remember: A penny saved is a penny earned! 🪙",
    "Your wallet called - it's feeling lighter already! 💸",
    "Making budgeting fun, one chat at a time! ✨",
    "Warning: May cause unexpected bursts of financial responsibility! 📊"
]
footer = random.choice(footer_messages)
logger.debug(f"Selected footer message: {footer}")
st.markdown(f"*{footer}*") 