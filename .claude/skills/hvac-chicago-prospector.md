---
name: hvac-chicago-prospector
description: Finds 5 new small HVAC prospects in Chicago with minimal web presence
---

# HVAC Chicago Prospector Skill

Finds 5 new small HVAC shop prospects in the Chicago area with little or no web presence for outreach testing.

## Trigger Condition

Use this skill when you need to find new small HVAC prospects for testing outreach campaigns, specifically targeting 1-5 truck operations in Chicago land.

## Steps

1. **Search for prospects**
   - Use browser to search Google Maps for HVAC in specific Chicago neighborhoods (Irving Park, Albany Park, Dunning, Austin, Belmont Cragin, etc.)
   - Look for small operations with Google Business listings but minimal website presence
   - Prioritize businesses that are:
     - Family-owned or locally-operated names
     - Single address (not multi-location chains)
     - Basic/no website or parked domain pages
     - Google Business listing only

2. **Verify minimal web presence**
   - Note if there's no website, only a Google Business profile
   - Check for parked domain pages or very basic landing pages
   - Record business name, address, and phone from Google Maps

3. **Extract contact info**
   - Try to find email in Google Business profile description
   - Search for the business name to find any email address
   - Note owner/manager name if visible in Google listing

4. **Check for duplicates**
   - Use Python/pandas to read `data/prospects_example.csv`
   - Check if business name already exists
   - Skip if already in the list

5. **Add new prospect to CSV**
   - Add row with columns: `Contacted?`, `Biz Name`, `Owner Name`, `Email Address`, `Phone #`, `Physical Address`, `Website`, `Notes`
   - Leave `Contacted?` blank (the email sender uses this as the trigger)
   - Mark `Email Address` as "unknown" if not found
   - `Website`: "N/A (no strong web presence)"
   - `Notes`: Include neighborhood, family-owned status, and any other relevant details

6. **Verify and document**
   - Print confirmation of new prospects added
   - Confirm CSV was updated successfully

**Avoid:**
- Large companies with multiple locations
- Commercial-only HVAC companies

## Pitfalls

- Don't confuse large regional HVAC companies with small local shops
- Many small HVAC companies don't have websites — this is ideal
- Check if a "website" is actually a parked domain or basic landing page
- Google Maps phone numbers are more reliable than stale website emails
- Owner names often appear in the Google Business description, not on the website
