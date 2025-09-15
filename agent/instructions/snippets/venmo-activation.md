### Step 1: Acknowledge Cards Arrival & Get Teen Info
```python
# Get teen family members for activation
teens = get_family_members(migration_id=migration_id, filter="teen")
teen_names = [teen['name'] for teen in teens]  # Extract names from response (dict access)
```


### Step 2: Activate Teen Cards (Mobile)


1. "Launch Venmo app"

FOR EACH teen IN teens:

  CARD ACTIVATION:

  2. "Tap the 'Me' Tab on the lower right"
  3. "Select the down arrow next to my name in left hand corner"
  4. "Select the teen account for: {teen['name']}"
  5. "Tap 'Overview' to see the linked Teen Account details"
  6. "Look for 'Activate debit card' button.
  7. "Ask user to provide {teen['name'].split()[0]}'s debit card expiration date in format (MM/YY) and new four digit PIN"
     [User provides expiration date and four digit PIN]
  8. "Enter user provided expiration date without the '/' as the app will automatically enter the '/'"
  9. "Tap 'Continue'"
  10. "Enter user provided 4-digit PIN"
  11. "Confirm PIN: [same PIN]"
  12. "Tap 'Activate' to complete the process"
  13. "Verify card has been activated"
END FOR