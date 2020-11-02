# OneNote to PDF Downloader

OneNote is an online, free service offered by Microsoft that allows you to take notes. I took the vast majority of my notes in the preclinical years of Medical School using OneNote. My workflow would be to import the slides for that lecture, then use my iPad/Apple Pencil to take hand written notes on top of the slides.

## Motivation
While OneNote is an excellent source for managing notes and personal documents, it is inherently closed source and backed up only to Microsoft. While I do currently have unlimited storage with Office365 provided by my school, there will come a day when OneNote may not be maintained and let to die. As I have made a significant investment in my preclinical knowledge and notes, I would like to save these.

Ideally, each page will be saved in PDF form. However, the built in exporters for OneNote (Native desktop application on Windows 10 *or* online at [OneNote.com](Onenote.com)) leave much to be desired (doesn't make clean page cuts, the width is the *maximum* width throughout the document, even if that means the rest of the document is very thin.). My ultimate goal is to export each page as one long PDF (to my knowledge, there is no limit to the length of PDF pages), allowing the user (me) to zoom in and out on a computer at a later date in high resolution.

## Organization
Within the preclinical years, there were six 'blocks' spanning 1.5 years. Within each block, there were 2-3 'modules'. Each module (15 in total) had it's own `notebook`. Within each notebook were multiple `sections`, which were the 'courses' as organized by GUSOM. Within each section, there were `pages`, some (if related to a main 'lecture' or 'activity') being 'subpages'.

## Mechanism

### OAuth
Microsoft provides [Microsoft Graph](https://developer.microsoft.com/en-us/graph), a service that allows easy API access to most/all Microsoft services, including OneNote. To access this, Microsoft authenticates users/developers with the OAuth 2.0 specification. I implemented custom functions to interact with this specification in the [OAuth](OAuth/) directory, specifically [oauth_helper.py](OAuth/oauth_helper.py). I also wrote custom handlers for getting the `access_code` back, also in that folder.

### InkML
OneNote saves ink annotations as [InkML](https://www.w3.org/TR/InkML/), which currently has a specification from W3C as of 2011-09-20, so quite out dated. I have not managed to find any javascript libraries that can render this code, so I have tried to write my own (incomplete).
