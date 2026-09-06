"""
Airtasker Scraper - Scrapes tasks from airtasker.com
"""
from apify import Actor
from playwright.async_api import async_playwright
import re

async def main():
    async with Actor:
        log = Actor.log
        log.info('Airtasker Scraper starting...')
        
        # Get input
        actor_input = await Actor.get_input() or {}
        max_results = actor_input.get('maxResults', 50)
        search_keyword = actor_input.get('searchKeyword', '')
        
        log.info(f'Config: maxResults={max_results}, keyword={search_keyword}')
        
        # Build URL
        if search_keyword:
            url = f"https://www.airtasker.com/tasks/?q={search_keyword}"
        else:
            url = "https://www.airtasker.com/tasks/"
        
        log.info(f'Fetching: {url}')
        
        # Use Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await page.wait_for_timeout(5000)  # Let page fully load
                
                log.info('Page loaded, extracting tasks...')
                
                # Extract tasks - simplified approach
                tasks = await page.evaluate("""
                    () => {
                        const results = [];
                        const taskLinks = document.querySelectorAll('a[href*="/tasks/"]');
                        
                        for (const link of taskLinks) {
                            const href = link.getAttribute('href');
                            
                            // Skip invalid links
                            if (!href || href === '/tasks/' || href.includes('?')) continue;
                            if (href.split('/').length < 3) continue;
                            
                            // Get the full URL
                            const fullUrl = href.startsWith('http') ? href : 'https://www.airtasker.com' + href;
                            
                            // Extract all text from the link
                            const text = link.textContent || '';
                            const lines = text.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
                            
                            if (lines.length === 0) continue;
                            
                            // First substantial line is usually the title
                            const title = lines[0];
                            
                            // Find price
                            const priceMatch = text.match(/\\$([\\d,]+)/);
                            const price = priceMatch ? '$' + priceMatch[1] : null;
                            
                            // Find offers
                            const offersMatch = text.match(/(\\d+)\\s+offer/i);
                            const offers = offersMatch ? parseInt(offersMatch[1]) : 0;
                            
                            // Location
                            let location = 'Not specified';
                            if (text.includes('Remote')) location = 'Remote';
                            else {
                                const locLine = lines.find(l => l.includes(',') || /^[A-Z][a-z]+/.test(l));
                                if (locLine) location = locLine;
                            }
                            
                            results.push({
                                title: title,
                                url: fullUrl,
                                price: price,
                                location: location,
                                offers: offers,
                                status: text.includes('Open') ? 'Open' : 'Unknown'
                            });
                        }
                        
                        return results;
                    }
                """)
                
                log.info(f'Extracted {len(tasks)} tasks from page')
                
                # Deduplicate by URL
                seen_urls = set()
                unique_tasks = []
                for task in tasks:
                    if task['url'] not in seen_urls:
                        seen_urls.add(task['url'])
                        unique_tasks.append(task)
                
                log.info(f'After dedup: {len(unique_tasks)} unique tasks')
                
                # Limit results
                if max_results and max_results > 0:
                    unique_tasks = unique_tasks[:max_results]
                
                # Push to dataset
                if unique_tasks:
                    await Actor.push_data(unique_tasks)
                    log.info(f'✅ Pushed {len(unique_tasks)} items to dataset')
                else:
                    log.warning('⚠️ No tasks extracted!')
                
            except Exception as e:
                log.error(f'Error: {e}')
                raise
            finally:
                await page.close()
                await browser.close()
        
        log.info('Airtasker Scraper finished')
