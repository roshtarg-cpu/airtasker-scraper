"""
Airtasker Scraper - Minimal working version
"""
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        Actor.log.info('Starting Airtasker Scraper...')
        
        # Get input
        actor_input = await Actor.get_input() or {}
        max_results = actor_input.get('maxResults', 10)
        
        Actor.log.info(f'Config: maxResults={max_results}')
        
        url = "https://www.airtasker.com/tasks/"
        Actor.log.info(f'Target: {url}')
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                Actor.log.info('Loading page...')
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)
                
                Actor.log.info('Extracting tasks...')
                
                # Simple extraction
                tasks = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href*="/tasks/"]'));
                        const results = [];
                        
                        for (const link of links) {
                            const href = link.getAttribute('href');
                            if (!href || href === '/tasks/' || href.includes('?')) continue;
                            
                            const text = link.textContent || '';
                            const lines = text.split('\\n').map(s => s.trim()).filter(Boolean);
                            
                            if (lines.length === 0) continue;
                            
                            const title = lines[0];
                            const priceMatch = text.match(/\\$([\\d,]+)/);
                            const price = priceMatch ? '$' + priceMatch[1] : null;
                            
                            results.push({
                                title: title,
                                url: 'https://www.airtasker.com' + href,
                                price: price,
                                location: text.includes('Remote') ? 'Remote' : 'Not specified'
                            });
                        }
                        
                        return results;
                    }
                """)
                
                Actor.log.info(f'Raw extracted: {len(tasks)} tasks')
                
                # Dedupe
                seen = set()
                unique = []
                for task in tasks:
                    if task['url'] not in seen:
                        seen.add(task['url'])
                        unique.append(task)
                
                # Limit
                final = unique[:max_results]
                
                Actor.log.info(f'Final: {len(final)} tasks (deduped & limited)')
                
                # Push
                if final:
                    await Actor.push_data(final)
                    Actor.log.info(f'✅ Pushed {len(final)} items')
                else:
                    Actor.log.warning('⚠️ No items to push')
                
            except Exception as e:
                Actor.log.error(f'Error: {str(e)}')
                raise
            finally:
                await page.close()
                await browser.close()
        
        Actor.log.info('Done!')
