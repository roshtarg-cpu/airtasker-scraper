"""
Airtasker Scraper - Scrapes tasks from airtasker.com
"""
from apify import Actor
from playwright.async_api import async_playwright
import re

async def _parse_proxy(proxy_url):
    """Parse proxy URL into Playwright proxy config"""
    if not proxy_url:
        return None
    
    # Expected format: http://user:pass@host:port
    match = re.match(r'http://([^:]+):([^@]+)@([^:]+):(\d+)', proxy_url)
    if match:
        return {
            'server': f'http://{match.group(3)}:{match.group(4)}',
            'username': match.group(1),
            'password': match.group(2)
        }
    return None

async def _fetch(url, proxy_url=None):
    """Fetch page content using Playwright"""
    async with async_playwright() as p:
        browser_args = {'headless': True}
        
        if proxy_url:
            proxy = await _parse_proxy(proxy_url)
            if proxy:
                browser_args['proxy'] = proxy
        
        browser = await p.chromium.launch(**browser_args)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            return content
        finally:
            await page.close()
            await browser.close()

async def _extract_tasks(page, log):
    """Extract task data from Airtasker page"""
    tasks = []
    
    # Extract tasks using page.evaluate
    task_data = await page.evaluate("""
        () => {
            const results = [];
            
            // Find all task links
            const taskLinks = document.querySelectorAll('a[href*="/tasks/"]');
            
            for (const link of taskLinks) {
                const href = link.getAttribute('href');
                if (!href || href === '/tasks/' || href.includes('?')) continue;
                
                // Extract text content from the link and surrounding elements
                const textContent = link.textContent || '';
                const parts = textContent.split('\\n').map(s => s.trim()).filter(Boolean);
                
                if (parts.length === 0) continue;
                
                // Parse components
                const title = parts[0];
                const location = parts.find(p => p.includes('Remote') || p.includes(',')) || 'Not specified';
                const priceMatch = textContent.match(/\$[\d,]+/);
                const price = priceMatch ? priceMatch[0] : null;
                
                // Extract offers count
                const offersMatch = textContent.match(/(\d+)\s+offer/);
                const offers = offersMatch ? parseInt(offersMatch[1]) : 0;
                
                results.push({
                    title: title,
                    url: 'https://www.airtasker.com' + href,
                    location: location,
                    price: price,
                    offers: offers,
                    status: parts.includes('Open') ? 'Open' : 'Unknown'
                });
            }
            
            return results;
        }
    """)
    
    log.info(f'Extracted {len(task_data)} tasks from page')
    return task_data

async def main():
    async with Actor:
        log = Actor.log
        log.info('Airtasker Scraper starting...')
        
        # Get input
        actor_input = await Actor.get_input() or {}
        category = actor_input.get('category', 'all')
        max_results = actor_input.get('maxResults', 50)
        use_proxy = actor_input.get('useProxy', False)
        
        log.info(f'Config: category={category}, maxResults={max_results}, useProxy={use_proxy}')
        
        # Get proxy if enabled
        proxy_url = None
        if use_proxy:
            import os
            proxy_password = (
                os.getenv('APIFY_PROXY_PASSWORD') or
                Actor.get_env().get('proxy_password')
            )
            if proxy_password:
                proxy_url = f"http://auto:{proxy_password}@proxy.apify.com:8000"
                log.info('Using Apify proxy (RESIDENTIAL)')
        
        # Build URL
        if category and category != 'all':
            url = f"https://www.airtasker.com/tasks/?category={category}"
        else:
            url = "https://www.airtasker.com/tasks/"
        
        log.info(f'Fetching: {url}')
        
        # Use Playwright to fetch
        async with async_playwright() as p:
            browser_args = {'headless': True}
            
            if proxy_url:
                proxy = await _parse_proxy(proxy_url)
                if proxy:
                    browser_args['proxy'] = proxy
            
            browser = await p.chromium.launch(**browser_args)
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Extract tasks
                tasks = await _extract_tasks(page, log)
                
                # Limit results
                if max_results and max_results > 0:
                    tasks = tasks[:max_results]
                
                log.info(f'Scraped {len(tasks)} tasks (limited to {max_results})')
                
                # Push to dataset
                if tasks:
                    await Actor.push_data(tasks)
                    log.info(f'Pushed {len(tasks)} items to dataset')
                else:
                    log.warning('No tasks extracted!')
                
            finally:
                await page.close()
                await browser.close()
        
        # Save task info
        env = Actor.get_env()
        await Actor.set_value('SAVED-TASK', {
            'actorId': env.get('actor_id'),
            'actorRunId': env.get('actor_run_id'),
            'defaultDatasetId': env.get('default_dataset_id'),
            'itemCount': len(tasks) if tasks else 0
        })
        
        log.info('Airtasker Scraper finished')
