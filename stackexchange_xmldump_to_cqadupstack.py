#!/usr/bin/env python

import os, re, sys
import xml.etree.ElementTree as ET
import datetime, json, codecs, glob
import zipfile, shutil, subprocess

def main(catdir, outputdir):
    catfiles = sorted(glob.glob(catdir + '/*7z'))
    cqadupstackforums = ['android', 'english', 'gaming', 'gis', 'mathematica', 'physics', 'programmers', 'stats', 'tex', 'unix', 'webmasters', 'wordpress']
    for catfile in catfiles:
	cat = os.path.basename(catfile).split('.')[0]
	if cat not in cqadupstackforums:
	    continue # we are only interested in twelve particular forums
	print '---------------------------'
	subforumdir = outputdir + '/' + cat + '/'
	jsonzip = outputdir + '/' + cat + '.zip'
	if os.path.exists(jsonzip):
	    print "Zipfile for cat", cat, "already exists. Skipping this subforum."
	elif os.path.exists(subforumdir):
            print "Output directory already exists: " + subforumdir
            print "Please remove it, or choose a different output directory."
            print "Skipping this subforum."
	else:
            make_json(catfile, outputdir)
            #read_json(catfile)


def read_json(catfile): # For testing
    category = os.path.basename(catfile).split('.')[0]
    basedir = os.path.dirname(catfile)

    inputfilename = basedir + '/' + category + '/' + category + '.json'
    f_open = codecs.open(inputfilename, 'r', encoding="utf-8")
    postsandanswers = json.load(f_open)
    print "Loaded json."

def make_json(catfile, outputdir):
    postdict, answerdict, commentdict, userdict = getmeallinfo(catfile)

    category = os.path.basename(catfile).split('.')[0]
    basedir = os.path.dirname(catfile)
    subforumdir = outputdir + '/' + category + '/'
    os.mkdir(subforumdir)

    outputfilename = subforumdir + category + "_questions.json"
    outputf = codecs.open(outputfilename, 'w', encoding="utf-8")
    json.dump(postdict, outputf, encoding="utf-8")

    outputfilename = subforumdir + category + "_answers.json"
    outputf = codecs.open(outputfilename, 'w', encoding="utf-8")
    json.dump(answerdict, outputf, encoding="utf-8")

    outputfilename = subforumdir + category + "_comments.json"
    outputf = codecs.open(outputfilename, 'w', encoding="utf-8")
    json.dump(commentdict, outputf, encoding="utf-8")

    outputfilename = subforumdir + category + "_users.json"
    outputf = codecs.open(outputfilename, 'w', encoding="utf-8")
    json.dump(userdict, outputf, encoding="utf-8")

    print "Unfortunately python zipfile truncates the files sometimes, so you'll have to manually zip these files:"

    #os.chdir(outputdir)
    #zf = zipfile.ZipFile(category + '.zip', mode='w')
    #zf.write(category + '/' + category + "_questions.json")
    #zf.write(category + '/' + category + "_answers.json")
    #zf.write(category + '/' + category + "_users.json")
    #zf.close()
    #shutil.rmtree(category)

    #print 'Made ' + category + '.zip with the following files:'
    print category + '/' + category + "_questions.json"
    print category + '/' + category + "_answers.json"
    print category + '/' + category + "_comments.json"
    print category + '/' + category + "_users.json"

def getmeallinfo(catfile):
    category = os.path.basename(catfile).split('.')[0]
    unzip_cat(catfile, category)

    postdict, answerdict  = read_posts(catfile) # This needs to happen first to be able to filter out answer dups from PostLinks.xml.
    postdict, answerdict, commentdict  = read_comments(catfile, postdict, answerdict)
    postdict = read_postlinks(postdict, catfile)
    userdict = get_user_info(postdict, answerdict, catfile)

    return postdict, answerdict, commentdict, userdict

def read_posts(catfile):
    '''This method reads the Posts file of the given category and fills and returns postdict'''
    category = os.path.basename(catfile).split('.')[0]
    basedir = os.path.dirname(catfile)

    filename = basedir + '/' + category + "/Posts.xml"
    postdict = {}
    answerdict = {}

    with open(filename) as fileobject:
        totaln = 0
        n = 1
        for line in fileobject: # To know for big files how fast we're reading them.
            if n == 100000:
                totaln += n
                print "Read", totaln, "lines of", category # stackoverflow has 19881020 lines
                n = 1
            n += 1
            if re.search('<row', line):
		xmlline = '<?xml version="1.0"?><data>' + line + '</data>'
		root = ET.fromstring(xmlline)
		for row in root: # This is only 'row'
		    if row.attrib['PostTypeId'] == '1': # 1 = Question, 2 = Answer. We're only interested in questions. 4-7 not a clue what they mean...
			postid = row.attrib['Id']
			postdict[postid] = {}
			if 'OwnerUserId' not in row.attrib or row.attrib['OwnerUserId'] == '-1':
			    postdict[postid]["userid"] = False # Or should I leave this out completely?
			else:
                            postdict[postid]["userid"] = row.attrib['OwnerUserId'] 
			postdict[postid]['body'] = row.attrib['Body']
			postdict[postid]['title'] = row.attrib['Title']
			postdict[postid]["creationdate"] = row.attrib['CreationDate']
                        postdict[postid]["related"] = []
                        postdict[postid]["dups"] = []
			postdict[postid]["viewcount"] = int(row.attrib['ViewCount'])
                        #postdict[postid]["answercount"] = row.attrib['AnswerCount'] # We've got a list of answers, so we can get the count from there.
			postdict[postid]['answers'] = []
                        if 'AcceptedAnswerId' in row.attrib:
                            postdict[postid]["acceptedanswer"] = row.attrib['AcceptedAnswerId']
                        else:
                            postdict[postid]["acceptedanswer"] = False # Or should I leave this out completely?
                        if 'FavoriteCount' in row.attrib:
                            postdict[postid]["favoritecount"] = int(row.attrib['FavoriteCount'])
                        else:
                            postdict[postid]["favoritecount"] = 0
                        postdict[postid]["score"] = int(row.attrib['Score'])
                        #postdict[postid]["commentcount"] = row.attrib['CommentCount'] # We've got a list of comments, so we can get the count from there.
			postdict[postid]["comments"] = []
			if 'Tags' in row.attrib:
                            tagstring = re.sub('<', '', row.attrib['Tags'])
                            tags = tagstring.split('>')[:-1] # The last item is always the empty string.
			    postdict[postid]["tags"] = tags

		    elif row.attrib['PostTypeId'] == '2': # It is an answer. Store it separately.
			answerid = row.attrib['Id']
			answerdict[answerid] = {}
			answerdict[answerid]['parentid'] = row.attrib['ParentId']
			answerdict[answerid]['body'] = row.attrib['Body']
			answerdict[answerid]['creationdate'] = row.attrib['CreationDate']
			answerdict[answerid]["score"] = int(row.attrib['Score'])
                        #answerdict[answerid]["commentcount"] = int(row.attrib['CommentCount']) # We've got a list of comments, so we can get the count from there.
			answerdict[answerid]["comments"] = []
			if 'OwnerUserId' not in row.attrib:
                            answerdict[answerid]["userid"] = False
                        else:
                            answerdict[answerid]["userid"] = row.attrib['OwnerUserId']
			
		    #else the posttype id is 3, 4, 5, 6, or 7 and the readme does not tell us what that means. So we'll skip those.
		    # I think posttype 6 means meta posts.

    
    for answer in answerdict:
	parentid = answerdict[answer]['parentid']
	postdict[parentid]['answers'].append(answer)

    return postdict, answerdict


def read_comments(catfile, postdict, answerdict):
    '''This method reads the Comments file of the given category, adds the comments to postdict and answerdict and returns a commentdict on top of that.'''
    category = os.path.basename(catfile).split('.')[0]
    basedir = os.path.dirname(catfile)

    filename = basedir + '/' + category + "/Comments.xml"
    commentdict = {}

    with open(filename) as fileobject:
        totaln = 0
        n = 1
        for line in fileobject: # To know for big files how fast we're reading them.
            if n == 100000:
                totaln += n
                print "Read", totaln, "lines of", category # stackoverflow has 19881020 lines
                n = 1
            n += 1
            if re.search('<row', line):
                xmlline = '<?xml version="1.0"?><data>' + line + '</data>'
                root = ET.fromstring(xmlline)
                for row in root: # This is only 'row'
		    commentid = row.attrib['Id']
		    parentid = row.attrib['PostId']
                    commentdict[commentid] = {}
		    commentdict[commentid]['score'] = int(row.attrib['Score'])
		    parentid = row.attrib['PostId']
		    commentdict[commentid]['parentid'] = parentid
		    commentdict[commentid]['body'] = row.attrib['Text']
		    commentdict[commentid]['creationdate'] = row.attrib['CreationDate']
		    if 'UserId' in row.attrib and row.attrib['UserId'] != -1:
		        commentdict[commentid]['userid'] = row.attrib['UserId']
		    else:
			commentdict[commentid]['userid'] = False
		    if parentid in postdict:
			commentdict[commentid]['parenttype'] = 'question'
			postdict[parentid]['comments'].append(commentid)
		    elif parentid in answerdict:
			commentdict[commentid]['parenttype'] = 'answer'
			answerdict[parentid]['comments'].append(commentid)
		    else:
			#print "Could not find parentid", parentid, "either in the posts or the answers..."
			#print xmlline
			del commentdict[commentid]

    return postdict, answerdict, commentdict


def read_postlinks(postdict, catfile):
    '''This function reads the PostLinks file and fills and returns dupslist'''
    category = os.path.basename(catfile).split('.')[0]
    basedir = os.path.dirname(catfile)

    filename = basedir + '/' + category + "/PostLinks.xml"
    with open(filename) as fileobject:
        totaln = 0
        n = 1
        for line in fileobject:
            if n == 100000:
                totaln += n
                print category + " -- Read", totaln, "lines." # stackoverflow has 1681973 lines
                n = 1
            n += 1
            if re.search('<row', line):
		xmlline = '<?xml version="1.0"?><data>' + line + '</data>'
                root = ET.fromstring(xmlline)
                for row in root: # This is only 'row'
                    linktypeid = row.attrib['LinkTypeId'] # 1 = linked, 3 = duplicate
		    postid = row.attrib['PostId']
		    dupid = row.attrib['RelatedPostId']
		    if postid not in postdict or dupid not in postdict:
                        # This means one of them is an answer post, not an initial post, so we're not interested in this combo.
                        continue
		    if int(postid) < int(dupid): #postid lower than dupid is unusual, but can happen when two duplicates are posted on the same day.
			if linktypeid == '1':
                            postdict[dupid]["related"].append(postid)
                        else: #linktypeid == '3'
                            postdict[dupid]["dups"].append(postid)
                    else:
		        if linktypeid == '1':
			    postdict[postid]["related"].append(dupid)
		        else: #linktypeid == '3'
			    postdict[postid]["dups"].append(dupid)

    # Deduplicate list of dup combos and related combos. Is this necessary? Tested: no, this is not necessary.
    return postdict
 

def get_user_info(postdict, answerdict, catfile):
    category = os.path.basename(catfile).split('.')[0]
    users_filename = os.path.dirname(catfile) + '/' + category + '/Users.xml'
    userdict = {}
    with open(users_filename) as fileobject:
        totaln = 0
        n = 1
        for line in fileobject: # To know for big files how fast we're reading them.
            if n == 100000:
                totaln += n
                print "Read", totaln, "lines of Users.xml of", category
                n = 1
            n += 1
            if re.search('<row', line):
                xmlline = '<?xml version="1.0"?><data>' + line + '</data>'
                root = ET.fromstring(xmlline)
                for row in root: # This is only 'row'
                    userid = row.attrib['Id']
                    if userid != '-1':
                        userdict[userid] = {}
                        userdict[userid]['rep'] = int(row.attrib['Reputation'])
                        userdict[userid]['views'] = int(row.attrib['Views'])
                        userdict[userid]['upvotes'] = int(row.attrib['UpVotes'])
                        userdict[userid]['downvotes'] = int(row.attrib['DownVotes'])
			userdict[userid]['date_joined'] = row.attrib['CreationDate']
			userdict[userid]['lastaccessdate'] = row.attrib['LastAccessDate']
                        if 'Age' in row.attrib:
                            userdict[userid]['age'] = int(row.attrib['Age'])
			userdict[userid]['answers'] = []
			userdict[userid]['questions'] = []
			userdict[userid]['badges'] = []

    # add badges
    badges_filename = os.path.dirname(catfile) + '/' + category + '/Badges.xml'
    with open(badges_filename) as fileobject:
        totaln = 0
        n = 1
        for line in fileobject: # To know for big files how fast we're reading them.
            if n == 100000:
                totaln += n
                print "Read", totaln, "lines of Users.xml of", category
                n = 1
            n += 1
            if re.search('<row', line):
                xmlline = '<?xml version="1.0"?><data>' + line + '</data>'
                root = ET.fromstring(xmlline)
                for row in root: # This is only 'row'
		    userid = row.attrib['UserId']
		    badge = row.attrib['Name']
		    if userid != '-1':
			if userid in userdict:
		            userdict[userid]['badges'].append(badge)

    # add postids and answerids.
    for post in postdict:
	if postdict[post]['userid']:
	    userid = postdict[post]['userid']
	    if userid in userdict:
	        userdict[userid]['questions'].append(post)
    for answer in answerdict:
	if answerdict[answer]['userid']:
	    userid = answerdict[answer]['userid']
	    if userid in userdict:
	        userdict[userid]['answers'].append(answer)
	    else:
		pass # The user is unknown so we cannot add this answer to the userdict
		
    return userdict



def unzip_cat(catfile, category):
    '''This function unzips the 7z files of a particular category'''
    print 'Catfile =', catfile
    basedir = os.path.dirname(catfile)
    if os.path.exists(basedir + '/' + category):
        if category == 'stackoverflow':
            print 'Unzipping in', basedir + '/' + category + '/'
            if os.path.basename(catfile) == 'PostLinks.xml':
                if not os.path.exists(basedir + '/' + category + '/PostLinks.xml'):
                    outputcatdir = '-o' + basedir + '/' + category + '/'
                    subprocess.call(['7za', 'e', catfile, outputcatdir])
            elif not os.path.exists(basedir + '/' + category + '/Posts.xml'):
                outputcatdir = '-o' + basedir + '/' + category + '/'
                subprocess.call(['7za', 'e', catfile, outputcatdir])
        else:
            print category + " -- Already unzipped."
    else:
        print 'Unzipping in', basedir + '/' + category + '/'
        outputcatdir = '-o' + basedir + '/' + category + '/'
        subprocess.call(['7za', 'e', catfile, outputcatdir])
    return


def usage():
    usage_text = '''
    This script can be used to turn the StackExchange data set into json files for CQADupStack.

    USAGE: ''' + os.path.basename(__file__) + ''' <subforumdir> <outputdir>

    <subforumdir> is the directory with all the StackExchange 7z subforum files.
    <outputdir> is the directory that the json files will be placed in.

    '''
    print usage_text
    sys.exit(' ')

#-------------------------------
if __name__ == "__main__":
    if len(sys.argv[1:]) != 2:
        usage()
    else:
        main(sys.argv[1], sys.argv[2])
                
                
