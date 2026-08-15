# Tutorials

## Fetch the API for the first time
You can pull the JSON data directly into your application without running the scraper. The [V5](../v5.json) dataset is hosted on GitHub Pages. Use a standard HTTP GET request to retrieve it.

```javascript
async function loadCardData() {
  const response = await fetch("[https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v5.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v5.json)");
  const cards = await response.json();
  
  console.log(cards[0].name, cards[0].share_code);
}
```

## Set up the local environment

To run the scraper yourself, you need Python 3.9+ installed on your machine.

1. Clone the repository to your local machine.
2. Open a terminal and navigate to the project directory.
3. Install the required dependencies.
```pip install -r requirements.txt```
4. Run the scraper against a set code. Preferably, one that is either incomplete or doesn't exist within the current [v5.json](../v5.json).
```bash 
python3 scripts/add_expansion.py b4a
```