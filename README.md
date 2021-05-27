# Custom Crypto Discord Bot
- written using primarily python 

## Current commands
### General
- `!help`
  - Displays information about the commands installed  
    

- `!ping`
  - Gets the current latency of the bot to the server

    
- `!coin <symbol pair>`
  - Gets the current value of a coin pair based on the Binance API
    
### Wallet
- `!wallet show`
  - Displays all the stored coins in the wallet, including the quantity, purchase time, purchase price,
    total coin value, and overall net worth of wallet based on current Binance prices formatted in an embed


- `!wallet depoist <coin> [price] <quantity>`
  - Adds a coin with the given price and quantity to a virtual wallet, stored in an offsite database
    if no price is given, will use the current price according to Binance
    

- `!wallet remove <coin> <price> <quantity> <date> <time> `
  - Removes an entry from the wallet


- `!wallet send <server id>`
  - Transfers all wallet entries to the provided server id from the current one, assuming they are running this bot
    

- `!wallet get <server id>`
  - Transfers all wallet entries from the provided server id to the current one, assuming they are running this bot
    

- `!wallet purge`
  - Removes all entries of a wallet, associated to the current server
   
## TODO
- [ ] Add a music feature that allows users to send the bot to a channel, and play music
- [ ] Add a numerical selection system for `!wallet remove` to allow users to remove an entry based on it's listing number or id
- [ ] Update the help command to utilize a coroutine rather than a hardcoded function, this way help messages can more efficiently be managed 
- [ ] Add a referral system that allows server members to manage everyone's referrals for different applications more easily 
- [ ] Add a live ticker system that uses channel names to track the current price of selected currencies 
- [ ] Add the ability to search for more information related to a currency, including 24hr volumes, chart options, market cap...

---
If any bugs are found or any suggestions are made, please feel free to post it in the issues tab and alert Tammon23 (Ikenna) or nohack11 (Bill Shema)
