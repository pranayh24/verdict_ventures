import spacy
import re
from collections import Counter, defaultdict
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from string import punctuation
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime
import numpy as np


class CommercialLegalSummarizer:
    def __init__(self):
        """Initialize the summarizer with commercial case specific configurations."""
        self.nlp = spacy.load('en_core_web_sm')

        # Commercial case specific keywords and phrases
        self.commercial_terms = {
            'contract_terms': [
                'breach of contract', 'consideration', 'offer', 'acceptance',
                'performance', 'termination', 'damages', 'liability'
            ],
            'financial_terms': [
                'damages', 'compensation', 'liquidated damages', 'monetary relief',
                'costs', 'interest', 'penalty', 'payment', 'settlement'
            ],
            'business_entities': [
                'corporation', 'llc', 'partnership', 'company', 'firm',
                'enterprise', 'business', 'joint venture'
            ],
            'commercial_actions': [
                'breach', 'default', 'terminate', 'execute', 'perform',
                'deliver', 'pay', 'settle', 'negotiate'
            ]
        }

        # Define importance weights for different aspects
        self.weights = {
            'monetary_value': 2.0,
            'key_dates': 1.5,
            'party_names': 1.3,
            'contract_terms': 1.8,
            'judgement': 2.0
        }

        # Extended stopwords for commercial cases
        self.commercial_stopwords = set([
            'plaintiff', 'defendant', 'court', 'case', 'hereby',
            'whereas', 'pursuant', 'hereinafter', 'said'
        ])
        self.stop_words = set(stopwords.words('english')).union(self.commercial_stopwords)

    def extract_monetary_values(self, text):
        """Extract and categorize monetary values from the text."""
        # Pattern for matching monetary values
        money_pattern = r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:million|billion|trillion))?'
        matches = re.finditer(money_pattern, text)

        monetary_dict = {
            'damages': [],
            'costs': [],
            'settlements': [],
            'other': []
        }

        for match in matches:
            amount = match.group()
            context = text[max(0, match.start() - 50):min(len(text), match.end() + 50)]

            # Categorize based on context
            if any(term in context.lower() for term in ['damage', 'compensation']):
                monetary_dict['damages'].append(amount)
            elif 'cost' in context.lower():
                monetary_dict['costs'].append(amount)
            elif 'settle' in context.lower():
                monetary_dict['settlements'].append(amount)
            else:
                monetary_dict['other'].append(amount)

        return monetary_dict

    def extract_parties(self, text):
        """Extract and classify parties involved in the commercial case."""
        doc = self.nlp(text)
        parties = {
            'plaintiffs': set(),
            'defendants': set(),
            'other_parties': set()
        }

        # Look for organization names and classify them
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PERSON']:
                context = text[max(0, ent.start_char - 20):min(len(text), ent.end_char + 20)].lower()

                if 'plaintiff' in context:
                    parties['plaintiffs'].add(ent.text)
                elif 'defendant' in context:
                    parties['defendants'].add(ent.text)
                else:
                    parties['other_parties'].add(ent.text)

        return {k: list(v) for k, v in parties.items()}

    def extract_key_dates(self, text):
        """Extract important dates and associated events."""
        doc = self.nlp(text)
        dates = {}

        for ent in doc.ents:
            if ent.label_ == 'DATE':
                # Get surrounding context
                sent = next((sent for sent in doc.sents if ent.start >= sent.start and ent.end <= sent.end), None)
                if sent:
                    context = sent.text
                    # Categorize date based on context
                    if any(term in context.lower() for term in ['filed', 'commenced', 'initiated']):
                        dates['case_filing'] = (ent.text, context)
                    elif any(term in context.lower() for term in ['contract', 'agreement', 'signed']):
                        dates['contract_date'] = (ent.text, context)
                    elif any(term in context.lower() for term in ['breach', 'default', 'violation']):
                        dates['breach_date'] = (ent.text, context)
                    elif any(term in context.lower() for term in ['judgment', 'decided', 'ruled']):
                        dates['judgment_date'] = (ent.text, context)

        return dates

    def extract_contract_elements(self, text):
        """Extract and analyze key contract elements."""
        elements = {
            'obligations': [],
            'breaches': [],
            'remedies': [],
            'terms': []
        }

        doc = self.nlp(text)

        # Pattern matching for contract elements
        for sent in doc.sents:
            sent_text = sent.text.lower()

            if any(term in sent_text for term in ['shall', 'must', 'required to']):
                elements['obligations'].append(sent.text)

            if any(term in sent_text for term in ['breach', 'violation', 'failed to']):
                elements['breaches'].append(sent.text)

            if any(term in sent_text for term in ['damages', 'remedy', 'relief', 'compensate']):
                elements['remedies'].append(sent.text)

            if any(term in sent_text for term in ['term', 'condition', 'provision']):
                elements['terms'].append(sent.text)

        return elements

    def generate_commercial_summary(self, text):
        """Generate a comprehensive summary focused on commercial aspects."""
        try:
            # Extract all relevant components
            monetary_values = self.extract_monetary_values(text)
            parties = self.extract_parties(text)
            dates = self.extract_key_dates(text)
            contract_elements = self.extract_contract_elements(text)

            # Format summary sections
            summary_parts = []

            # Case parties
            summary_parts.append("PARTIES INVOLVED:")
            if parties['plaintiffs']:
                summary_parts.append("Plaintiff(s): " + ", ".join(parties['plaintiffs']))
            if parties['defendants']:
                summary_parts.append("Defendant(s): " + ", ".join(parties['defendants']))

            # Key dates
            if dates:
                summary_parts.append("\nKEY DATES:")
                for event, (date, context) in dates.items():
                    summary_parts.append(f"{event.replace('_', ' ').title()}: {date}")

            # Monetary aspects
            if any(monetary_values.values()):
                summary_parts.append("\nMONETARY ASPECTS:")
                for category, amounts in monetary_values.items():
                    if amounts:
                        summary_parts.append(f"{category.title()}: {', '.join(amounts)}")

            # Contract elements
            if any(contract_elements.values()):
                summary_parts.append("\nKEY CONTRACT ELEMENTS:")
                for category, elements in contract_elements.items():
                    if elements:
                        summary_parts.append(f"\n{category.title()}:")
                        summary_parts.extend([f"- {element}" for element in elements[:3]])

            return "\n".join(summary_parts)

        except Exception as e:
            return f"Error generating commercial summary: {str(e)}"

    def analyze_case_outcome(self, text):
        """Analyze and summarize the case outcome and reasoning."""
        doc = self.nlp(text)

        outcome = {
            'decision': None,
            'reasoning': [],
            'damages_awarded': None,
            'key_findings': []
        }

        # Look for judgment indicators
        judgment_section = False
        for sent in doc.sents:
            sent_text = sent.text.lower()

            if any(term in sent_text for term in ['court finds', 'court concludes', 'it is ordered']):
                judgment_section = True

            if judgment_section:
                if any(term in sent_text for term in ['grant', 'deny', 'dismiss']):
                    outcome['decision'] = sent.text
                elif 'damages' in sent_text:
                    outcome['damages_awarded'] = sent.text
                elif any(term in sent_text for term in ['because', 'therefore', 'thus', 'accordingly']):
                    outcome['reasoning'].append(sent.text)
                elif any(term in sent_text for term in ['finds', 'concludes', 'determines']):
                    outcome['key_findings'].append(sent.text)

        return outcome


summarizer = CommercialLegalSummarizer()

case_text = """D.N. Jeevaraj vs Chief Sec., Govt. Of Karnataka & Ors on 27 November, 2015
Equivalent citations: 2015 AIR SCW 6528, 2016 (2) SCC 653, 2016 (1) AKR 97, AIR 2016 SC (CIVIL) 699, (2015) 8 MAD LJ 885, (2016) 2 JCR 130 (SC), (2016) 1 KANT LJ 353, (2016) 1 ORISSA LR 179, (2016) 2 PAT LJR 104, (2015) 12 SCALE 672, (2016) 1 JLJR 502, (2016) 1 CLR 300 (SC), (2016) 1 ALL WC 443, (2016) 1 CAL HN 72, 2016 (3) KCCR SN 277 (SC)
Author: Madan B. Lokur
Bench: Madan B. Lokur, S.A. Bobde
                                                                              REPORTABLE

                        IN THE SUPREME COURT OF INDIA

                        CIVIL APPELLATE JURISDICTION

                       CIVIL APPEAL NO. 13785 OF 2015
                (Arising out of S.L.P. (C) No. 37226 OF 2012)


D.N. Jeevaraj                                    ….Appellant

                                       versus

Chief Secretary,
Govt. of Karnataka & Ors.                        …Respondents

                                    WITH

                       CIVIL APPEAL NO. 13786  OF 2015
                 (Arising out of S.L.P. (C) No. 38453/2012)


D.V. Sadananada Gowda                        .….Appellant

                                       versus

K.G. Nagalaxmi Bai & Ors.                    ….Respondents


                               J U D G M E N T
Madan B. Lokur, J.

1. Leave granted in both petitions.

2. The question for consideration is whether the appellants (Sadananda Gowda and Jeevaraj) have per se violated the terms of the lease-cum-sale agreement that they have individually entered into with the Bangalore Development Authority (for short ‘the BDA’) by constructing a multi- storeyed residential building on the plots allotted to them. The alternative question is whether the construction made by them is contrary to the plan sanctioned by the Bruhat Bangalore Mahanagara Palike (for short ‘the BBMP’) and thereby violated the lease-cum-sale agreement with the BDA. The term of the lease-cum-sale agreement alleged to have been violated is clause 4 which reads as follows:

“4. The Lessee/Purchaser shall not sub-divide the property or construct more than one dwelling house in it.
The expression ‘dwelling house’ means building constructed to be used wholly for human habitation and shall not include any apartments to the building whether attached thereto or not, used as a shop or a building of warehouse or building in which manufactory operations are conducted by mechanical power or otherwise.
(a) The Lessee shall plant at least two trees in the site leased to him.”
3. In our opinion, both the questions are required to be answered in the negative. There has been no violation of the lease-cum-sale agreement or the sanction plan for construction such as to violate the lease-cum-sale agreement with the BDA.

The facts

4. On or about 5th March, 2002 Sadananda Gowda (the then Deputy Leader of the Opposition in the Legislative Assembly in Karnataka) addressed a letter to the Chief Minister of Karnataka requesting for allotment of a plot from the Bangalore Development Authority. This request was favourably considered and he was allotted plot No. 2-B in HSR layout, Sector-3, Bangalore measuring 50 ft x 80 ft. on 30th August, 2006 in terms of the Bangalore Development Authority (Site Allotment) Rules, 2006.[1] In accordance with the required formalities, Sadananda Gowda executed an affidavit on 1st September, 2006 in the form of an undertaking with the BDA in which it was stated as follows:-

“4. In the event that any false statements or declarations furnished and sworn to and declared in this Affidavit and in the event that I violate any conditions of site allotment, the Authorities are empowered to resume such building and site without granting any compensation to me and BDA is entitled to and empowered to resume the site for which BDA is authorized and I hereby declare so and I hereby swear accordingly.” Pursuant to the execution of the affidavit and completion of all necessary administrative formalities, the BDA executed a lease-cum-sale agreement in favour of Sadananda Gowda on 2nd February, 2007 and on the same day handed over possession of the plot to him.
5. As far as Jeevaraj is concerned, he too made a request on or about 14th September, 2004 for the allotment of a plot to the Chief Minister of Karnataka and was allotted a plot by the BDA. Subsequently and on his request, the allotment was changed to plot no. 13-B in HSR layout, Sector- 3, Bangalore on 30th October, 2008. The area of Jeevaraj’s plot is also 50 ft. x 80 ft. and it is adjacent to the plot allotted to Sadananda Gowda. Jeevaraj too completed all necessary administrative formalities and was handed over possession of the plot on 24th November, 2008.

6. On 4th June, 2009 both Sadananda Gowda and Jeevaraj moved an application before the BDA to amalgamate their plots. The request was rejected by the BDA and communicated to them on 24th September, 2009 and there is no dispute or doubt with regard to the validity of the reasons for turning down the proposal for amalgamation.

7. Thereafter, both Sadananda Gowda and Jeevaraj made separate applications for sanction of a building plan to the BBMP. The building plans were for the construction of a ground/stilt floor and two upper floors. The plans were considered by the BBMP and sanctioned on 22nd July, 2010. At this stage, it may be noted that there was some confusion with regard to the sanctioned construction but during the course of hearing it was clarified that the sanction was for a ground/stilt floor and two upper floors.

8. Based on the sanction so granted, the construction of the buildings began on the plots owned by Sadananda Gowda and Jeevaraj.

9. On 2nd August, 2011 the Bangalore Mirror newspaper carried a story alleging that Sadananda Gowda was making an illegal construction on the plot allotted to him and Jeevaraj by amalgamating the two plots. The newspaper carried photographs of the construction which showed one composite building under construction on the two plots and it was alleged that the building under construction was a five storeyed building. It was also alleged that a part of the building was to be used for commercial purposes although the allotment was for a residential purpose.

10. Apparently based on the newspaper report (and perhaps her own research) one Nagalaxmi Bai filed a Writ Petition in the Karnataka High Court on 4th August, 2011 wherein a prayer was made for a declaration that the building being constructed on the plots above mentioned having been allotted to Sadananda Gowda by the BDA is an illegally constructed building and that the BDA ought to resume the site along with the building and forfeit any amount paid in this behalf by Sadananda Gowda. The parties to the writ petition were the State of Karnataka (respondent Nos. 1 and 2), the BDA (respondent No. 3), the Commissioner of Police (respondent No. 4 but later deleted) and Sadananda Gowda (respondent No. 5). Later, the BBMP was impleaded as respondent No. 6 and Jeevaraj was impleaded as respondent No. 7 in the High Court.

11. For the record, it may be mentioned that on 4th August, 2011 the day the writ petition was filed, Sadananda Gowda was appointed as the Chief Minister of Karnataka.

12. The essence of the grievance of Nagalaxmi Bai was that first of all the two adjacent plots were amalgamated despite refusal by the BDA and a composite or consolidated building was impermissibly constructed on them and therefore there was a per se violation of the lease-cum-sale deed entered into by Sadananda Gowda and Jeevaraj with the BDA. Secondly the constructed building was not in conformity with the sanctioned plan approved by the BBMP and therefore there was a violation of the lease-cum- sale agreement with the BDA and the affidavit in the form of an undertaking given to the BDA. It was also alleged that contrary to the lease-cum-sale deed, the building was intended to be used for commercial purposes. These were the three principal grievances raised by Nagalaxmi Bai.

13. The High Court admitted the writ petition and issued notice to the respondents on 10th January, 2012.

14. In the meanwhile, Sadananda Gowda and Jeevaraj moved applications for modification of the sanctioned building plan. There is no dispute that this was permissible. The request was considered by the BBMP and on 26th September/3rd October, 2011 sanction was granted for the construction of a basement, ground floor and three upper floors on each plot. After admission of the writ petition, the modified building plan was further modified on the request of Sadananda Gowda and Jeevaraj and construction was permitted by the BBMP on 12th June/22nd June, 2012 for a building having a basement, ground floor and three upper floors entirely for residential purposes.

Responses in the High Court

15. In response to the writ petition, affidavits were filed by the BDA, the BBMP, Sadananda Gowda and Jeevaraj.

16. The BDA denied that the two plots in question had been amalgamated and it also stated that it had no role in the sanctioning of building plans. The BBMP stated that the allegation that a five storeyed building had been constructed was not correct nor was it correct that the building was being used for commercial purposes. In fact, it was submitted that the construction had not been completed and so it could not be assumed that the building was in violation of the sanctioned building plans or was to be used for commercial purposes. Attention was drawn to Section 310 of the Karnataka Municipal Corporations Act, 1976[2] which provided that a building cannot be occupied or permitted to be occupied without permission from the Commissioner.[3] It was submitted that Sadananda Gowda would be permitted to occupy the building only after an inspection of the building and compliance with the sanctioned plan.

17. The BBMP further stated (in the additional statement of objections filed on 9th October, 2012 just a few days before judgment was delivered) that the permissible floor area ratio of the plot in question is 2.25 and the permissible coverage is 65%. However, since Sadananda Gowda had purchased transferable development rights, he is entitled to a floor area ratio of 3.60 and permissible coverage is 82.5%. The BBMP gave a chart of the permissible floor area ratio, the permissible coverage area and what has been achieved in the modified sanctioned plan. This is as follows:

|S.No. |Details            |As per the      |Achieved as against   |
|      |                   |modified plan   |the modified plan     |
|1.    |Permissible floor  |3.60            |2.562                 |
|      |area ratio         |                |                      |
|2.    |Permissible        |82.50%          |64.03%                |
|      |coverable area     |                |                      |

It was specifically stated by the BBMP that “The modified plan now sanctioned is purely for residential purpose.” The BBMP further stated that an inspection of the building was carried out by the Assistant Director, Town Planning and Assistant Executive Engineer of the BBMP with reference to the sanctioned plan. During the inspection, certain deviations were noticed and appropriate action would be taken in that regard under the Karnataka Municipal Corporations Act and that an occupancy certificate would be issued only after the BBMP is satisfied that the construction meets the requirements of law.

18. Sadananda Gowda also filed an affidavit in the High Court in which he denied any violation of the lease-cum-sale agreement or the sanctioned building plan. He denied that a five storeyed building was constructed or that the two plots in question were amalgamated. He submitted that an area of 20% could be earmarked for commercial activity and that he had not violated the sanctioned building plan. Jeevaraj also filed a more or less similar affidavit emphasizing, however, that no relief was claimed against him in the writ petition.

Decision of the High Court

19. After going through the affidavits filed by the various parties and after hearing learned counsel, the High Court allowed the writ petition filed by Nagalaxmi Bai by its impugned judgment and order dated 19th October, 2012. The High Court held that the two plots of Sadananda Gowda and Jeevaraj were amalgamated despite the refusal to grant permission to do so by the BDA and also that a ‘homogenous structure’ had come up on the amalgamated plots. There was, therefore, a violation of condition No. 4 of the lease-cum-sale agreement. The High Court also held that the building plan sanctioned by the BBMP on 22nd July, 2010 was in violation of condition No. 4 of the lease-cum-sale agreement and that the subsequent modifications were an exercise in ‘belated damage control’. The High Court considered the decision of this Court in R & M Trust v. Koramangala Residents Vigilance Group[4] and held it inapplicable to the facts of the case. Accordingly, the High Court quashed the orders sanctioning the building construction plans in favour of Sadananda Gowda and Jeevaraj by the BBMP and directed the BDA to take action against them in terms of condition No. 4 of the lease-cum-sale agreement as well as the affidavit in the form of an undertaking given by them to the BDA for abiding by the terms and conditions thereof and the allotment rules.

20. The sum and substance of the decision of the High Court is to be found in paragraph 53 and paragraph 61 thereof and these read as follows:

“53. From the facts pleaded and materials on record and even the averments as contained in the statements of objections filed on behalf of respondents and annexures such as photographs produced by the petitioner and the respondents, it cannot be disputed nor in any manner doubted that a homogenous structure which has been characterized as one plus four floors or otherwise, had been put up and this construction has come up after rejection of a joint request of the fifth and seventh respondents for amalgamating the two sites and putting up a commercial complex or combined structure, is a structure which is flawed from the very beginning and is clearly in contravention of the order passed by BDA rejecting the request of the fifth and seventh respondents for amalgamating the two sites. Apart from enabling provisions of the building byelaws and zonal regulations, which are brought to our attention, which may, perhaps, enable a modification of the plans and a revised plan may be permitted, if all is within the limits of law and not prohibited by a basic law. In the instant case, as is pointed out by the learned counsel for the petitioner, the construction initially was in violation of condition No. 4 of the lease-cum- sale agreement and also therefore violating affidavit of undertaking.” Paragraph 61 of the decision of the High Court reads as follows:
“61. The municipal authority, if at all, is only concerned with the building plan being in conformity with the zonal regulations and the building bye-laws. At the same time, conditions that are incorporated in the lease-cum-sale agreement are also to be looked into. The manner in which the initial plan is sanctioned by the municipal authorities approving construction of ground plus two floors in itself indicates that they are overlooking condition No. 4 of the lease-cum-sale agreement. Whether this initial plan can be characterized as a valid one or otherwise, it is obviously one overlooking one of the conditions of allotment and therefore the allottees, who are very much aware of the conditions imposed on them by BDA, cannot take advantage of this plan sanctioned by BBMP to sustain their action which is initially flawed and contrary to the terms of allotment to contend that it is based on a valid initial plan and revised plans as permitted in law as per the bye-laws etc.”
21. Feeling aggrieved, Sadananda Gowda and Jeevaraj have preferred these appeals.

Discussion

22. It appears to us, on a plain reading of condition No. 4 of the lease- cum-sale agreement that it is breached or violated under three circumstances: (i) If the plot is sub-divided or (ii) If more than one building is constructed thereon for the purposes of human habitation or

(iii) If an apartment whether attached to the building or not is used as a shop or a warehouse etc.

23. As far as the first circumstance is concerned, there is no allegation that either Sadananda Gowda or Jeevaraj have sub-divided their respective plot. The allegation (though denied) is to the contrary, which is that they have amalgamated their plots. Assuming the allegation is substantiated, it can be said at best, that they have acted contrary to the letter dated 24th September, 2009 but there is no breach or violation of condition No. 4 of the lease-cum-sale agreement. The effect, if any, of acting contrary to the letter dated 24th September, 2009 has not been canvassed or agitated. In any event, the case set up by Nagalaxmi Bai is not of a violation of the letter dated 24th September, 2009 but of a violation of condition No. 4 of the lease-cum-sale agreement. Under these circumstances, frankly, we fail to understand how it has been found by the High Court that amalgamation of the two plots (assuming it to be so) is a breach or violation of the lease-cum-sale agreement. Be that as it may, factually there is no sub-division of the plots and to that extent there is no violation of condition No. 4 of the lease-cum-sale agreement.

24. As regards the second and third circumstance, it is nobody’s case that more than one building has been constructed on either of the plots or that the building or any part thereof is used as a shop or warehouse etc. Therefore, this need not detain us any further, more particularly since the buildings are not yet completely constructed.

25. The grievance of Nagalaxmi Bai is that the photographs of the building indicate that the construction on the two plots is actually a composite or a combined or a homogenous structure and that construction is per se in violation of condition No.4 of the lease-cum-sale agreement. It is her further grievance that after the writ petition was filed both Sadananda Gowda and Jeevaraj made some changes and demolished a part of the structure by way of damage control so that it appears that there is a separate building on each plot. It is submitted that once the condition of the lease-cum-sale agreement is breached, the demolition of a part of the combined or composite or homogenous structure cannot undo or remedy the violation that has already occurred.

26. We are not in agreement with the contention advanced on behalf of Nagalaxmi Bai in this regard. The writ petition was filed by her at a time when the construction was in progress – in fact, it is still not complete. It is true that substantial progress was made in the construction but nevertheless Sadananda Gowda and Jeevaraj could make changes therein until the grant of an occupancy certificate by the BBMP. It would be a bit far- fetched to assume, in a case such as the present, that an incomplete structure that can be modified is per se contrary to the building bye-laws or the lease-cum-sale agreement especially when changes or modifications could be made therein. Corrective measures can always be made by the owner of a building until an occupancy certificate or a completion certificate is granted. It is perhaps pursuant to this ‘entitlement’ to make changes that both Sadananda Gowda and Jeevaraj appreciated that were the structure to remain as it is, an occupancy certificate might not be granted by the BBMP and that is perhaps why there was a partial demolition of the structure. They cannot be faulted for taking corrective steps, however belated, whether they were voluntary or prompted by the writ petition, or otherwise.

27. An analogy may be drawn in this connection with regard to deviations that sometimes come up in constructed buildings. Some deviations are compoundable and some are not and those that are not compoundable are required to be rectified before an occupancy certificate or a completion certificate is granted. Merely because a building has some deviations from the sanctioned plan, either at the initial stage or later on in the construction, does not necessarily mean that the construction is per se illegal unless the deviations are irremediable, in which event an occupancy certificate or completion certificate will not be granted. Changes and modifications may be made as required by the building bye-laws or by the municipal authority and this is precisely what has happened so far as the present case is concerned, which is that to bring the construction in conformity with the building regulations, a part of the building was demolished by Sadananda Gowda and Jeevaraj. The stage at which the modifications are made is not of any consequence, as long as they are made before the occupancy certificate or a completion certificate is granted.

28. Nagalaxmi Bai is also aggrieved that multi-storeyed constructions have come up on the two plots. Like it or not, condition No. 4 of the lease- cum-sale agreement does not prohibit the construction of a multi-storeyed building on the plot as long as the construction is of a dwelling house which is used wholly for human habitation and not as a shop or a warehouse or for other commercial purposes. As long as the building conforms to the terms of the lease-cum-sale agreement and the building regulations and bye- laws, no objection can be taken to the construction, however large or ungainly it might be. In this regard, the BDA is on record to specifically say that there is no violation of the lease-cum-sale agreement and the BBMP is on record to say that there is no violation of the sanctioned plan, except for some deviations. The BBMP is also on record to say that unless the buildings are in conformity with the sanctioned plan and the building regulations, no occupancy certificate will be granted to Sadananda Gowda and Jeevaraj. The matter should rest at that.

29. In our opinion, the High Court was in error in coming to the conclusion that the buildings constructed on the two plots were not in accordance with the sanctioned plan. The buildings were and are still under construction and it is too early to say that there has been a violation of the sanctioned plan. No doubt there are some deviations as pointed out by the BBMP but that is a matter that can certainly be attended to by Sadananda Gowda and Jeevaraj on the one hand and the BBMP on the other. The mere existence of some deviations in the buildings does not lead to any definite conclusion that there is either a breach or a violation of condition No. 4 of the lease-cum-sale agreement or the building plan sanctioned by the BBMP.

30. Another grievance of Nagalaxmi Bai is that the construction is such that the building is capable of being used as a commercial complex. For instance, some photographs show that shutters have been put up and the contention is that actually some shops have been constructed with shutters. As mentioned above, the building is not yet complete and we cannot guess why shutters have been put up by Sadananda Gowda and Jeevaraj. There might or might not be a good reason for it. Nothing can be assumed either way. We also cannot ignore the contention put forward that 20% of the building can be permissibly used for a commercial purpose. If the putting up of shutters is suggestive of unlawful commercial use of a part of the building, the BDA and the BBMP will certainly consider the matter for whatever it is worth, including whether 20% of the building can be commercially exploited or not.

31. It is finally contended that what we are effectively required to do is to lift the veil, so to speak, and appreciate that Sadananda Gowda is an influential politician and can muscle his way with the statutory authorities. The contention is that Sadananda Gowda was (and is) an influential politician in Karnataka and was also its Chief Minister at the relevant time and that made it impossible for any of the statutory authorities to come to any conclusion adverse to his interest despite an ex facie and egregious violation of condition No. 4 of the lease-cum-sale agreement. It is difficult to accept such a blanket and free-wheeling submission, particularly in the absence of any material on record. That apart, it may be recalled that even when Sadananda Gowda applied for amalgamation of his plot with that of Jeevaraj, he was an influential politician in Karnataka being the Deputy Leader of the Opposition. Notwithstanding this, the BDA rejected the request of amalgamating his plot with that Jeevaraj’s plot. Additionally, even while Nagalaxmi Bai’s writ petition was pending in the High Court and Sadananda Gowda was the Chief Minister of Karnataka, an inspection of the premises was carried out by the Assistant Director, Town Planning and the Assistant Executive Engineer of the BBMP. They pointed out certain deviations in the construction and the BBMP did state on affidavit that appropriate action would be taken in this regard and that an occupancy certificate would be issued only after the BBMP is satisfied that the construction is in accordance with law. It is difficult to assume, under these circumstances, that Sadananda Gowda exercised his influence as the Chief Minister of Karnataka to arm-twist the BBMP since the inspection report was not entirely in his favour.

32. This is not to say that in no circumstance can a statutory body not be influenced by a politician who has considerable clout. A lot depends on the facts of each case and the surrounding circumstances. Insofar as the present case is concerned, in spite of the clout that Sadananda Gowda may have wielded in Karnataka, his actions relating to the construction of the building on his plot of land do not suggest any abuse, as mentioned above. Undoubtedly, there are some deviations in the construction which will surely be taken care of by the BBMP which has categorically stated on affidavit that an occupancy certificate will be given only if the building constructed conforms to the sanctioned plan and the building bye-laws.

33. In view of the above, we find no good reason to uphold the order passed by the High Court allowing the writ petition and it is accordingly set aside.

Public interest litigation

34. Learned counsel for the parties addressed us on the question of the bona fides of Nagalaxmi Bai in filing a public interest litigation. We leave this question open and do not express any opinion on the correctness or otherwise of the decision of the High Court in this regard.

35. However, we note that generally speaking, procedural technicalities ought to take a back seat in public interest litigation. This Court held in Rural Litigation and Entitlement Kendra v. State of U.P.[5] to this effect as follows:

“The writ petitions before us are not inter-partes disputes and have been raised by way of public interest litigation and the controversy before the court is as to whether for social safety and for creating a hazardless environment for the people to live in, mining in the area should be permitted or stopped. We may not be taken to have said that for public interest litigations, procedural laws do not apply. At the same time it has to be remembered that every technicality in the procedural law is not available as a defence when a matter of grave public importance is for consideration before the court.”
36. A considerable amount has been said about public interest litigation in R & M Trust and it is not necessary for us to dwell any further on this except to say that in issues pertaining to good governance, the courts ought to be somewhat more liberal in entertaining public interest litigation. However, in matters that may not be of moment or a litigation essentially directed against one organization or individual (such as the present litigation which was directed only against Sadananda Gowda and later Jeevaraj was impleaded) ought not to be entertained or should be rarely entertained. Other remedies are also available to public spirited litigants and they should be encouraged to avail of such remedies.

37. In such cases, that might not strictly fall in the category of public interest litigation and for which other remedies are available, insofar as the issuance of a writ of mandamus is concerned, this Court held in Union of India v. S.B. Vohra[6] that:

“Mandamus literally means a command. The essence of mandamus in England was that it was a royal command issued by the King’s Bench (now Queen’s Bench) directing performance of a public legal duty.
A writ of mandamus is issued in favour of a person who establishes a legal right in himself. A writ of mandamus is issued against a person who has a legal duty to perform but has failed and/or neglected to do so. Such a legal duty emanates from either in discharge of a public duty or by operation of law. The writ of mandamus is of a most extensive remedial nature. The object of mandamus is to prevent disorder from a failure of justice and is required to be granted in all cases where law has established no specific remedy and whether justice despite demanded has not been granted.”
38. A salutary principle or a well recognized rule that needs to be kept in mind before issuing a writ of mandamus was stated in Saraswati Industrial Syndicate Ltd. v. Union of India[7] in the following words:

“The powers of the High Court under Article 226 are not strictly confined to the limits to which proceedings for prerogative writs are subject in English practice. Nevertheless, the well recognised rule that no writ or order in the nature of a mandamus would issue when there is no failure to perform a mandatory duty applies in this country as well. Even in cases of alleged breaches of mandatory duties, the salutary general rule, which is subject to certain exceptions, applied by us, as it is in England, when a writ of mandamus is asked for, could be stated as we find it set out in Halsbury’s Laws of England (3rd Edn.), Vol. 13, p. 106):
“As a general rule the order will not be granted unless the party complained of has known what it was he was required to do, so that he had the means of considering whether or not he should comply, and it must be shown by evidence that there was a distinct demand of that which the party seeking the mandamus desires to enforce, and that that demand was met by a refusal.” In the cases before us there was no such demand or refusal. Thus, no ground whatsoever is shown here for the issue of any writ, order, or direction under Article 226 of the Constitution.”
39. It is not necessary for us to definitively pronounce on the contention of learned counsel for Sadananda Gowda and Jeevaraj that the litigation initiated by Nagalaxmi Bai was not a public interest litigation or that no mandamus ought to have been issued by the High Court since no demand was made nor was there any refusal to meet that demand. But we do find it necessary to reaffirm the law should a litigant be asked to avail of remedies that are not within the purview of public interest litigation. Exercise of discretion

40. Learned counsel for Sadananda Gowda and Jeevaraj also addressed us on the issue that the High Court had exceeded its jurisdiction in questioning the sanctioning of the building plans by the BBMP and further mandating the BDA to take action against Sadananda Gowda and Jeevaraj in terms of condition No. 4 of the lease-cum-sale agreement and the affidavit undertaking given by them, thereby effectively requiring the BDA to forfeit the lease.

41. This Court has repeatedly held that where discretion is required to be exercised by a statutory authority, it must be permitted to do so. It is not for the courts to take over the discretion available to a statutory authority and render a decision. In the present case, the High Court has virtually taken over the function of the BDA by requiring it to take action against Sadananda Gowda and Jeevaraj. Clause 10 of the lease-cum-sale agreement gives discretion to the BDA to take action against the lessee in the event of a default in payment of rent or committing breach of the conditions of the lease-cum-sale agreement or the provisions of law.[8] This will, of course, require a notice being given to the alleged defaulter followed by a hearing and then a decision in the matter. By taking over the functions of the BDA in this regard, the High Court has given a complete go-bye to the procedural requirements and has mandated a particular course of action to be taken by the BDA. It is quite possible that if the BDA is allowed to exercise its discretion it may not necessarily direct forfeiture of the lease but that was sought to be pre- empted by the direction given by the High Court which, in our opinion, acted beyond its jurisdiction in this regard.

42. In Mansukhlal Vithaldas Chauhan v. State of Gujarat[9] this Court held that it is primarily the responsibility and duty of a statutory authority to take a decision and it should be enabled to exercise its discretion independently. If the authority does not exercise its mind independently, the decision taken by the statutory authority can be quashed and a direction given to take an independent decision. It was said:

“Mandamus which is a discretionary remedy under Article 226 of the Constitution is requested to be issued, inter alia, to compel performance of public duties which may be administrative, ministerial or statutory in nature. Statutory duty may be either directory or mandatory. Statutory duties, if they are intended to be mandatory in character, are indicated by the use of the words “shall” or “must”. But this is not conclusive as “shall” and “must” have, sometimes, been interpreted as “may”. What is determinative of the nature of duty, whether it is obligatory, mandatory or directory, is the scheme of the statute in which the “duty” has been set out. Even if the “duty” is not set out clearly and specifically in the statute, it may be implied as correlative to a “right”.
In the performance of this duty, if the authority in whom the discretion is vested under the statute, does not act independently and passes an order under the instructions and orders of another authority, the Court would intervene in the matter, quash the order and issue a mandamus to that authority to exercise its own discretion.”
43. To this we may add that if a court is of the opinion that a statutory authority cannot take an independent or impartial decision due to some external or internal pressure, it must give its reasons for coming to that conclusion. The reasons given by the court for disabling the statutory authority from taking a decision can always be tested and if the reasons are found to be inadequate, the decision of the court to by-pass the statutory authority can always be set aside. If the reasons are cogent, then in an exceptional case, the court may take a decision without leaving it to the statutory authority to do so. However, we must caution that if the court were to take over the decision taking power of the statutory authority it must only be in exceptional circumstances and not as a routine. Insofar as the present case is concerned, the High Court has not given any reason why it virtually took over the decision taking function of the authorities and for this reason alone the mandamus issued by the High Court deserves to be set aside, apart from the merits of the case which we have already adverted to.

Conclusion

44. Therefore, whichever way the decision of the High Court is looked at, in our opinion, the conclusions arrived at and the directions given are not sustainable in law and are set aside. The appeals are accordingly allowed.



                                                               ...…………………….J
                                                         (Madan B. Lokur)


New Delhi;                               ...…………………….J   November  27,  2015
                            (S.A. Bobde)


-----------------------
[1] Learned counsel for Nagalaxmi Bai mentioned that the discretionary allotment was not warranted but that was not pressed nor is it an issue before us.

[2] Section 310 - Completion certificate and permission to occupy or use (1) Every person shall, within one month after the completion of the erection of a building or the execution of any such work, deliver or send or cause to be delivered or sent to the Commissioner at his office notice in writing of such completion, accompanied by a certificate in the form prescribed in the bye-laws signed and subscribed in the manner prescribed and shall give to the Commissioner all necessary facilities for the inspection of such buildings or of such work and shall apply for permission to occupy the building.

(1A) Notwithstanding anything contained in sub-section (1), where permission is granted to any person for erection of a building having more than one floor, such person shall, within one month after completion of execution of any of the floors of such building, deliver or send or cause to be delivered or sent to the Commissioner at his office, a notice in writing of such completion accompanied by a certificate in the form prescribed in the bye-laws, signed and subscribed in the manner prescribed and shall give to the Commissioner all necessary facilities for inspection of such floor of the building and may apply for permission to occupy such floor of the building.

(2) No person shall occupy or permit to be occupied any such building, or part of the building or use or permit to be used the building or part thereof affected by any work, until,-

(a) permission has been received from the Commissioner in this behalf, or

(b) The Commissioner has failed for thirty days after receipt of the notice of completion to intimate his refusal of the said permission. [3] This is usually known as a ‘completion certificate’ or an ‘occupancy certificate’ [4] (2005) 3 SCC 91 [5] 1989 Supp (1) SCC 504 [6] (2004) 2 SCC 150 [7] (1974) 2 SCC 630 [8] In the event of the Lessee/Purchaser committing default in the payment of rent or committing breach of any conditions of this agreement or the provisions of the Bangalore Development Authority, (Allotment of Sites) Rules, the Lessor/Vendor may determine the tenancy at any time after giving the Lessee/Purchaser fifteen days notice ending with the month of the tenancy, and take possession of the property. The Lessor/Vendor may also forfeit twelve and a half per cent of the amounts treated as security deposit under clause of these presents."""
# Generate comprehensive summary
summary = summarizer.generate_commercial_summary(case_text)
print("---------------------------------------------------------")
print("---------------------------------------------------------")
print("--------------------------Summary-------------------------------")
print(summary)

from flask import Flask

app = Flask(__name__)


@app.route('/summary', methods=['GET', 'POST'])
def predict():
    # Return the summary as plain text
    return summary


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)