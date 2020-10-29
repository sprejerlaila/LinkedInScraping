from threading import Thread
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

import time
import json

from webdriver_manager.chrome import ChromeDriverManager

from utils import ScrapingException, is_url_valid, HumanCheckException, wait_for_loading, wait_for_scrolling, \
    AuthenticationException

class Scraper(Thread):

    def __init__(self, linkedin_username, linkedin_password, profiles_urls, headless=False, output_file_path = "scrape_results.csv", ids = None):

        Thread.__init__(self)

        # Creation of a new instance of Chrome
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--no-sandbox')
        if headless:
            self.options.add_argument('--headless')

        self.browser = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=self.options)

        self.profiles_urls = profiles_urls
        self.ids = ids

        self.linkedin_username = linkedin_username
        self.linkedin_password = linkedin_password

        self.output_file_path = output_file_path

        
    def run(self):
        
        
        # Login in LinkedIn
        self.browser.get('https://www.linkedin.com/uas/login')
        
        # Add cookies
        cookies = [
        {'x-acbuk': '"GBEMY3O2hrKWNI7e@Pf4pIuZ@998tjCaFwx@swBsIO2Bzb@FDBA5b1matewtPivx"'},
        {'gt_userPref': 'lfsk:a2luZytzaXplK2JlZCtzaGVldHMscnVsZWQrbm90ZWJvb2ssd2hpdGVib2FyZA==|isSearchOpen:dHJ1ZQ==|recentAdsOne:Y2Fycy12YW5zLW1vdG9yYmlrZXM=|cookiePolicy:dHJ1ZQ==|recentAdsTwo:Zm9yLXNhbGU=|location:dWs='},
        {'gt_tm': '8eb554fd-00b1-4b8a-8abb-8d1a43bed8e5'},
        {'gt_s': 'sc:MQ==|ar:aHR0cDovL3d3dy5ndW10cmVlLmNvbS9zZWFyY2g/c2VhcmNoX2NhdGVnb3J5PWFsbCZxPWtpbmclMjBzaXplJTIwYmVkJTIwc2hlZXRz|st:MTYwMDYzMTA4NjcyOA==|clicksource_featured:|sk:a2luZyBzaXplIGJlZCBzaGVldHM=|clicksource_nearby:|id:bm9kZTAxN3FlYTF0YXl1NXEwMTN1OWx2cGcyM293NDgyNDQ1Nw==|clicksource_natural:MTM4NDkyMTczOCwxMzg0NjU3MzQyLDEzNjkzMTgwNzAsMTM4NDU0NDM5NywxMzQyODkzMTkzLDEzODMyMTMxOTcsMTM4MjgyMjc3MSwxMzgyODIyNTMzLDEzODI4MjE5ODIsMTM4MjMyODc5MA=='}
        ]

        for c in cookies:
            self.browser.add_cookie({"name": list(c.keys())[0], "value": list(c.values())[0]})

        username_input = self.browser.find_element_by_id('username')
        username_input.send_keys(self.linkedin_username)

        password_input = self.browser.find_element_by_id('password')
        password_input.send_keys(self.linkedin_password)
        password_input.submit()
        
        if not self.browser.current_url == "https://www.linkedin.com/feed/":
                print(self.browser.current_url)
                time.sleep(40)
                raise AuthenticationException()

        
        for idx, linkedin_url in enumerate(self.profiles_urls):
            
            print("scraping profile: ", linkedin_url)
            scrape_results = self.scrape_profile(linkedin_url)

            if not scrape_results:
                
                ## Keep track of non-collected users
                with open(self.output_file_path + 'error_ids.csv', 'a') as f:
                     f.write("%s\n" % self.ids[idx])

                print("waiting 10 seconds")
                time.sleep(10)

            else:
                scrape_results['id'] = self.ids[idx]
                
                with open(self.output_file_path + 'scraped_profiles.json', 'a') as fp:
                        json.dump(scrape_results, fp)

                        fp.write('\n')
                
                # Keep track of collected users
                with open(self.output_file_path + 'collected_ids.csv', 'a') as f:
                        f.write("%s\n" % self.ids[idx])
                        
            time.sleep(3)


        self.browser.quit()

    def scrape_profile(self, linkedin_url, waiting_time=10):

        try:
            profile = self.__scrape_profile(linkedin_url)

        except HumanCheckException:
            captcha_solved = input("Press enter when captcha is solved or write 'skip' ")

            if captcha_solved == "skip":
                print('skiping profile')
                return None

            profile = self.scrape_profile(linkedin_url, int(waiting_time*1.5))

        except ScrapingException:
            profile = None

        return profile

    def __scrape_profile(self, profile_linkedin_url):

        if not is_url_valid(profile_linkedin_url):
            raise ScrapingException

        self.browser.get(profile_linkedin_url)
        

        # Check correct loading of profile and eventual Human Check
        if not str(self.browser.current_url).strip() == profile_linkedin_url.strip():
            if self.browser.current_url == 'https://www.linkedin.com/in/unavailable/':
                raise ScrapingException
            else:
                raise HumanCheckException

        self.load_full_page()

        # SCRAPING

        try:
            profile_name = self.scrape_profile_name()
            print("profile name: ", profile_name)
        except:
            raise ScrapingException

        title = self.scrape_title()
        contacts = self.scrape_contacts() # get number of contacts
        about = self.scrape_about()

        time.sleep(1)

        educations = self.scrape_education()
        volunteering = self.scrape_volunteering()
        skills = self.scrape_skills() ### TODO ADD NUMBER OF VALIDATIONS

        time.sleep(1)

        certifications = self.scrape_certifications()
        accomplishments = self.scrape_accomplishments()
        recommendations = self.scrape_recommendations()

        time.sleep(1)

        interests = self.scrape_interests()
        jobs = self.scrape_jobs()  # keep as last scraping



        if len(educations) == 0 and len(jobs) == 0:
            return None

        return {"name": profile_name, "title":title, "contacts": contacts, "about": about, "skills": skills, \
                "jobs": jobs, "education": educations, "volunteering": volunteering, "certifications": certifications,\
                "accomplishments": accomplishments, "recommendations": recommendations, "interests": interests}



    def scrape_profile_name(self):
        return self.browser.execute_script(
            "return document.getElementsByClassName('pv-top-card--list')[0].children[0].innerText")

    def scrape_title(self):
        return self.browser.execute_script(
            "return document.getElementsByClassName('pv-top-card')[0].getElementsByTagName('h2')[0].innerText")

    def scrape_contacts(self):
        return self.browser.execute_script(
            "return document.getElementsByClassName('pv-top-card')[0].getElementsByClassName('pv-top-card--list')[1].getElementsByTagName('li')[1].innerText")

    def scrape_about(self):
        try:
            self.browser.execute_script(
                "document.getElementsByClassName('pv-about__summary-text')[0].getElementsByClassName('lt-line-clamp__more')[0].click()")
        except WebDriverException:
            return []

        try:
            about = self.browser.execute_script(
            "return document.getElementsByClassName('pv-about__summary-text')[0].innerText")
        except:
            about = ""
        
        return about


    def scrape_jobs(self):
        try:
            jobs = self.browser.execute_script(
                "return ("
                    "function(){ "
                        "var jobs = []; var els = document.getElementById('experience-section').getElementsByTagName('ul')[0].getElementsByTagName('li');"
                        "for (var i=0; i<els.length; i++){ "
                            "try { var els2 = els[i].getElementsByTagName('ul')[0].getElementsByTagName('li'); "
                                "for (var j=0; j<els2.length; j++){  "
                                    "if(els2[j].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                                        "  if(els2[j].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                                        "     } else { "
                                                    "try { position = els2[j].getElementsByTagName('h3')[0].getElementsByTagName('span')[1].innerText; } "
                                                    "catch(err) { position = ''; }"
                                                    "try { company_name = els[i].getElementsByClassName('pv-entity__company-summary-info')[0].getElementsByTagName('h3')[0].getElementsByTagName('span')[1].innerText; }"
                                                    "catch (err) { company_name = ''; }"
                                                    "try{  date_ranges = els2[j].getElementsByClassName('pv-entity__date-range')[0].getElementsByTagName('span')[1].innerText; }"
                                                    "catch (err) {date_ranges = ''; } "
                                                    "try{  job_location = els2[j].getElementsByClassName('pv-entity__location')[0].getElementsByTagName('span')[1].innerText; }"
                                                    "catch (err) {job_location = ''; } "
                                                    "try{ company_url = els[i].getElementsByTagName('a')[0].href;} catch (err) {company_url = ''; } "
                                                    "try { els2[j].getElementsByClassName('pv-entity__extra-details')[0].getElementsByClassName('inline-show-more-text__button')[0].click(); } catch(err) {debug = 'error';}"
                                                    "try{ job_description = els2[j].getElementsByClassName('pv-entity__extra-details')[0].getElementsByClassName('pv-entity__description')[0].innerText;} catch (err) {job_description = ''; }"
                                                    "jobs.push([position, company_name, company_url, date_ranges, job_location, job_description]);"
                                                "}"
                                    "}"
                                 "}"
                            "}"

                            "catch (err) {"
                                    "if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                                    "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                                    "       } else {"
                                                "try { position = els[i].getElementsByClassName('pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;} "
                                                "catch(err) {position = ''; } "

                                                "try { company_name = els[i].getElementsByClassName('pv-entity__summary-info')[0].getElementsByClassName('pv-entity__secondary-title')[0].innerText;} "
                                                "catch (err) { company_name = ''; } "
                                                
                                                "try{ date_ranges = els[i].getElementsByClassName('pv-entity__summary-info')[0].getElementsByClassName("
                                                "'pv-entity__date-range')[0].getElementsByTagName('span')[1].innerText;       } catch (err) {"
                                                "date_ranges = ''; }  "
                                                
                                                "try{ job_location = els[i].getElementsByClassName('pv-entity__summary-info')[0].getElementsByClassName('pv-entity__location')[0].getElementsByTagName("
                                                "'span')[1].innerText;       } catch (err) {job_location = ''; }"
                                                
                                                "try{ company_url = els[i].getElementsByTagName('a')[0].href;} catch (err) {company_url = ''; } "
                                                
                                                "try { els[i].getElementsByClassName('pv-entity__extra-details')[0].getElementsByClassName('inline-show-more-text__button')[0].click(); } catch(err) {debug = 'error';}"
                                                "try{ job_description = "
                                                "els[i].getElementsByClassName('pv-entity__extra-details')[0].getElementsByClassName('pv-entity__description')[0].innerText;} catch (err) {job_description = ''; }       jobs.push("
                                                "[position, company_name, company_url, date_ranges, job_location, job_description]); }"
                                                "}"
                            "} "
                        "} "
                    "return jobs; })();"

                )
        except WebDriverException:
            jobs = []

        parsed_jobs = []

        for job in jobs:
            if job[0] == "":
                continue
            if job[2] != "":
                time.sleep(1)
                company_industry, company_employees = self.scrape_company_details(job[2])
                
            parsed_jobs.append({
                "position": job[0],
                "company": {
                    "name": job[1],
                    "industry": company_industry,
                    "employees": company_employees
                    },
                "location": job[4],
                "date_range":job[3],
                "job_description":job[5]
                }
            )
        
        return parsed_jobs

    def scrape_volunteering(self):
        try:
            volunteerings = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'volunteering-section')[0].getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         position = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "position = ''; }    try {         cause = els[i].getElementsByClassName("
                "'pv-entity__cause')[0].getElementsByTagName('span')[1].innerText;       }       catch(err) { "
                "position = ''; }    try {         company_name = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByClassName('pv-entity__secondary-title')[0].innerText;     "
                "  } catch (err) { company_name = ''; }        try{         date_ranges = els["
                "i].getElementsByClassName('pv-entity__summary-info')[0].getElementsByClassName("
                "'pv-entity__date-range')[0].getElementsByTagName('span')[1].innerText;       } catch (err) {"
                "date_ranges = ''; }        try{         job_location = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByClassName('pv-entity__location')[0].getElementsByTagName("
                "'span')[1].innerText;       } catch (err) {job_location = ''; }        try{         company_url = "
                "els[i].getElementsByTagName('a')[0].href;       } catch (err) {company_url = ''; }        jobs.push("
                "[position, company_name, company_url, date_ranges, job_location, cause]);     }   } } return jobs; })();")
        except WebDriverException:
            volunteerings = []

        parsed_volunteerings = []

        for volunteering in volunteerings:
            
            parsed_volunteerings.append({
                "position": volunteering[0],
                "company": volunteering[1],
                "cause": volunteering[5],
                "location": volunteering[4],
                "date_range":volunteering[3]

                }
            )
        
        return parsed_volunteerings

    def scrape_recommendations(self):
        
        ### Click on all 'show more recommendations'
        while True:
            try:
                self.browser.execute_script(
                    "document.getElementsByClassName('pv-recommendations-section')[0].getElementsByClassName('pv-profile-section__see-more-inline')[0].click()")

            except WebDriverException:
                break
        
        ###TODO
        ### Ugly way of expanding recommendations. Need to fix this
        counter = 0
        while True: 
            try:
                script = "document.getElementsByClassName('pv-recommendations-section')[0].getElementsByTagName('ul')[0].getElementsByTagName('li')[{}].innerText".format(counter)
                self.browser.execute_script("return " + script)
                try:
                    script = "document.getElementsByClassName('pv-recommendations-section')[0].getElementsByTagName('ul')[0].getElementsByTagName('li')[{}].getElementsByClassName('lt-line-clamp__more')[0].click()".format(counter)
                    self.browser.execute_script(script)
                    counter +=1 
                except:
                    pass
            except:
                break
                
        try:
            recommendations = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'pv-recommendations-section')[0].getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         recommender = els[i].getElementsByClassName("
                "'pv-recommendation-entity__detail')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "recommender = ''; } try {         recommender_position = els[i].getElementsByClassName("
                "'pv-recommendation-entity__detail')[0].getElementsByTagName('p')[0].innerText;       }       catch(err) { "
                "recommender_position = ''; } try {         recommender_relation = els[i].getElementsByClassName("
                "'pv-recommendation-entity__detail')[0].getElementsByTagName('p')[1].innerText;       }       catch(err) { "
                "recommender_relation = ''; } try { els[i].getElementsByClassName('pv-recommendation-entity__highlights')[0].getElementsByClassName('lt-line-clamp__more')[0].click(); } catch(err) {debug = 'error';} "

                "try {         text = els[i].getElementsByClassName("
                "'pv-recommendation-entity__highlights')[0].getElementsByTagName('div')[0].innerText;       }       catch(err) { "
                "text = ''; } jobs.push("
                "[recommender, recommender_position, recommender_relation, text]);     }   } } return jobs; })();")
        except WebDriverException:
            recommendations = []


        parsed_recommendations = []

        for recommendation in recommendations:           
            parsed_recommendations.append({
                "recommender": recommendation[0],
                "recommender_position": recommendation[1],
                "recommender_relation": recommendation[2],
                "text": recommendation[3]
                }
            )
        
        return parsed_recommendations

    def scrape_company_details(self, company_url):    
        self.browser.get(company_url)

        try:
            company_employees = self.browser.execute_script(
                "return document.querySelector('a[data-control-name" +
                '="topcard_see_all_employees"' +
                "]').innerText.split(' employees')[0].split(' ').lastObject;"
            )
        except WebDriverException:
            company_employees = ''

        try:
            company_industry = self.browser.execute_script(
                "return document.getElementsByClassName('org-top-card-summary-info-list__info-item')[0].innerText")
        except WebDriverException:
            company_industry = ''

        return company_industry, company_employees

    def scrape_skills(self):
        try:
            self.browser.execute_script(
                "document.getElementsByClassName('pv-skills-section__additional-skills')[0].click()")
        except WebDriverException:
            return []

        wait_for_loading()

        try:
            return self.browser.execute_script(
                "return (function(){els = document.getElementsByClassName('pv-skill-category-entity');results = ["
                "];for (var i=0; i < els.length; i++){results.push(els[i].getElementsByClassName("
                "'pv-skill-category-entity__name-text')[0].innerText);}return results;})()")
        except WebDriverException:
            return []

    def scrape_education(self):

        try:
            educations = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementById("
                "'education-section').getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         institution = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "institution = ''; }        try {         education_degree = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByClassName('pv-entity__secondary-title')[0].getElementsByTagName('span')[1].innerText;     "
                "  } catch (err) { education_degree = ''; }  try {         education_discipline = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByClassName('pv-entity__secondary-title')[1].getElementsByTagName('span')[1].innerText;     "
                "  } catch (err) { education_discipline = ''; }  try{         date_ranges = els["
                "i].getElementsByClassName('pv-entity__summary-info')[0].getElementsByClassName("
                "'pv-entity__dates')[0].getElementsByTagName('span')[1].innerText;       } catch (err) {"
                "date_ranges = ''; }        try{         job_location = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByClassName('pv-entity__location')[0].getElementsByTagName("
                "'span')[1].innerText;       } catch (err) {job_location = ''; }        try{         company_url = "
                "els[i].getElementsByTagName('a')[0].href;       } catch (err) {company_url = ''; }        jobs.push("
                "[institution, education_degree, education_discipline, company_url, date_ranges, job_location]);     }   } } return jobs; })();")
        except WebDriverException:
            educations = []

        parsed_educations = []

        for education in educations:
            parsed_educations.append({
                "institution": education[0],
                "degree": education[1],
                "discipline": education[2],
                "location": education[5],
                "date_range":education[4]
                }
            )
        
        return parsed_educations

    def scrape_certifications(self):

        try:
            certifications = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementById("
                "'certifications-section').getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         title = els[i].getElementsByClassName("
                "'pv-certifications__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "title = ''; }        try {         institution = els[i].getElementsByClassName("
                "'pv-certifications__summary-info')[0].getElementsByTagName('p')[0].getElementsByTagName('span')[1].innerText;     "
                "  } catch (err) { institution = ''; }  try{         date_ranges = els["
                "i].getElementsByClassName('pv-certifications__summary-info')[0].getElementsByTagName("
                "'p')[1].getElementsByTagName('span')[1].innerText;       } catch (err) {"
                "date_ranges = ''; }  jobs.push("
                "[title, institution, date_ranges]);     }   } } return jobs; })();")
        except WebDriverException:
            certifications = []

        
        parsed_certifications = []

        for certification in certifications:
            parsed_certifications.append({
                "title": certification[0],
                "institution": certification[1],
                "date": certification[2]
                }
            )
        
        return parsed_certifications
    
    def scrape_accomplishments(self):

        try:
            accomplishments = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'pv-accomplishments-section')[0].getElementsByTagName('div'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {  try {         categories = els[i].getElementsByTagName("
                "'div')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "categories = ''; }     try {         accomplishment = els[i].getElementsByTagName("
                "'div')[0].getElementsByTagName('div')[0].getElementsByTagName('ul')[0].innerText;       }       catch(err) { "
                "accomplishment = ''; }  jobs.push("
                "[categories, accomplishment]);     }   } } return jobs; })();")
        except WebDriverException:
            accomplishments = []
        
        parsed_accomplishments = []

        for accomplishment in accomplishments:

            if accomplishment[0] != "":
                parsed_accomplishments.append({
                    accomplishment[0]: accomplishment[1]
                    }
            )
        
        return parsed_accomplishments

    def scrape_interests(self):
        try:
            self.browser.execute_script(
                "document.getElementsByClassName('pv-interests-section')[0].getElementsByClassName('pv-profile-section__card-action-bar')[0].click()")
        except WebDriverException:
            pass

        wait_for_loading()

        parsed_influencers = []

        # Influencers
        try:
            self.browser.execute_script(
                "document.getElementById('pv-interests-modal__following-influencers').click()")

            interests = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'pv-interests-list')[0].getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         name = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "name = ''; }        try {         position = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('p')[0].innerText;     "
                "  } catch (err) { position = ''; }"
                "                    try {         followers = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('p')[1].innerText;     "
                "  } catch (err) { followers = ''; }  jobs.push("
                "[name, position, followers]);     }   } } return jobs; })();")

            for interest in interests:
                parsed_influencers.append({
                    "name": interest[0],
                    "position": interest[1],
                    "followers": interest[2]
                    })

        except WebDriverException:
            pass

        parsed_companies = []

        # Click companies details
        try:
            self.browser.execute_script(
                "document.getElementById('pv-interests-modal__following-companies').click()")

            wait_for_loading()

            interests = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'pv-interests-list')[0].getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         company = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "company = ''; }        try {         followers = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('p')[1].innerText;     "
                "  } catch (err) { followers = ''; }  jobs.push("
                "[company, followers]);     }   } } return jobs; })();")

            for interest in interests:
                parsed_companies.append({
                    "company": interest[0],
                    "followers": interest[1]
                    }
                )
        
        except WebDriverException:
            pass
        

        parsed_groups = []
        # Click companies details
        try:
            self.browser.execute_script(
                "document.getElementById('pv-interests-modal__following-groups').click()")

            wait_for_loading()

            interests = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'pv-interests-list')[0].getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         group = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "group = ''; }        try {         members = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('p')[1].innerText;     "
                "  } catch (err) { members = ''; }  jobs.push("
                "[group, members]);     }   } } return jobs; })();")

            for interest in interests:
                parsed_groups.append({
                    "group": interest[0],
                    "members": interest[1]
                    }
                )
        
        except WebDriverException:
            pass

        
        parsed_schools = []
        # Click companies details
        try:
            self.browser.execute_script(
                "document.getElementById('pv-interests-modal__following-schools').click()")

            wait_for_loading()

            interests = self.browser.execute_script(
                "return (function(){ var jobs = []; var els = document.getElementsByClassName("
                "'pv-interests-list')[0].getElementsByTagName('ul')[0].getElementsByTagName('li'); for (var i=0; "
                "i<els.length; i++){   if(els[i].className!='pv-entity__position-group-role-item-fading-timeline'){   "
                "  if(els[i].getElementsByClassName('pv-entity__position-group-role-item-fading-timeline').length>0){ "
                "     } else {       try {         school = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('h3')[0].innerText;       }       catch(err) { "
                "school = ''; }        try {         followers = els[i].getElementsByClassName("
                "'pv-entity__summary-info')[0].getElementsByTagName('p')[1].innerText;     "
                "  } catch (err) { followers = ''; }  jobs.push("
                "[company, followers]);     }   } } return jobs; })();")

            for interest in interests:
                parsed_schools.append({
                    "school": interest[0],
                    "followers": interest[1]
                    }
                )
        
        except WebDriverException:
            pass


        try:
            self.browser.execute_script("document.getElementsByClassName('artdeco-modal__dismiss')[0].click()")
        except WebDriverException:
            pass

        parsed_interests = {
        "infuencers": parsed_influencers, 
        "companies": parsed_companies, 
        "groups": parsed_groups,
        "schools": parsed_schools
        }
        
        return parsed_interests

    def load_full_page(self):
        window_height = self.browser.execute_script("return window.innerHeight")
        scrolls = 1
        while scrolls * window_height < self.browser.execute_script("return document.body.offsetHeight"):
            self.browser.execute_script('window.scrollTo(0, ' + str(window_height * scrolls) + ');')
            wait_for_scrolling()
            scrolls += 1

        for i in range(self.browser.execute_script(
                "return document.getElementsByClassName('pv-profile-section__see-more-inline').length")):
            try:
                self.browser.execute_script(
                    "document.getElementsByClassName('pv-profile-section__see-more-inline')[" + str(
                        i) + "].click()")
            except WebDriverException:
                pass

            wait_for_loading()
