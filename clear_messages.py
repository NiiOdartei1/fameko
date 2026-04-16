#!/usr/bin/env python
"""
Clear all chat messages and conversations from the database
"""
import sys
from app import create_app, db
from models import Message, Conversation

def clear_messages():
    app = create_app()
    
    with app.app_context():
        try:
            # Count before deletion
            message_count = Message.query.count()
            conversation_count = Conversation.query.count()
            
            print(f"📊 Current state:")
            print(f"   Messages: {message_count}")
            print(f"   Conversations: {conversation_count}")
            
            # Confirm deletion
            confirm = input("\n⚠️  Are you sure you want to delete ALL messages and conversations? (yes/no): ").lower().strip()
            if confirm != 'yes':
                print("❌ Cancelled.")
                return
            
            # Delete all messages first (foreign key constraint)
            deleted_messages = Message.query.delete()
            print(f"\n✓ Deleted {deleted_messages} messages")
            
            # Delete all conversations
            deleted_conversations = Conversation.query.delete()
            print(f"✓ Deleted {deleted_conversations} conversations")
            
            # Commit changes
            db.session.commit()
            print("\n✅ All chat data cleared successfully!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    clear_messages()
