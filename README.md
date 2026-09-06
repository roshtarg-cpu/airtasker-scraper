# Airtasker Scraper

Scrapes tasks from [Airtasker.com](https://www.airtasker.com/) - Australia's leading freelance and local services marketplace.

## Features

- 🎯 Extract task details including title, price, location, and offers
- 🔄 Configurable category filtering
- 📊 Customizable result limits
- 🌐 Optional proxy support for reliability

## Input

- **category** (string, default: "all") - Task category to scrape
- **maxResults** (integer, default: 50) - Maximum number of tasks to scrape
- **useProxy** (boolean, default: false) - Use Apify residential proxy

## Output

Each task includes:
- `title` - Task title
- `url` - Full URL to task detail page
- `location` - Task location (Remote, city, etc.)
- `price` - Task budget/price
- `offers` - Number of offers received
- `status` - Task status (Open, etc.)

## Example Output

```json
{
  "title": "Looking for someone who owns a Cricut!!",
  "url": "https://www.airtasker.com/tasks/...",
  "location": "Remote",
  "price": "$50",
  "offers": 0,
  "status": "Open"
}
```

## Usage

1. Choose your category (or leave as "all")
2. Set maximum results (1-1000)
3. Enable proxy if needed
4. Run and download results

## About Airtasker

Airtasker is Australia's most trusted marketplace for local services. Users post tasks, skilled people offer their services, and tasks get done.

## License

Apache 2.0
