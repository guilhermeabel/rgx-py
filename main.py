from pathlib import Path
from datetime import datetime
import sys
import re
import time

# app
appName = "Manda Bala"
appVersion = "v2.0"

# var def
selection = 1
fileList = []
fileDict = "./files.txt"
currentDir = Path('./').absolute()
dump = "./dump.php"

# regex patterns
enumStaticReference = re.compile(r'(Enum\\[\w]+::[\w]+)') # ................... Enum\Example::EXMPL
scopeResolutionOperator = re.compile(r'(^[^\\]([\w]+::\$[\w]+))') #............ Auth::$idExample
scopeResolutionOperatorBackslash = re.compile(r'(^\\([\w]+::\$[\w]+))') #...... \Auth::$idExample
multipleClassAttribute = r'(\$[\w]+->[\w]+(->[\w]+)+)' #....................... $class->attr->attr
classAttributeKey = r'(\$[\w]+->[\w]+\["[\w]+"\])' #........................... $class->attr["key"] 
classAttribute = r"(\$[\w]+->[\w]+)" #......................................... $class->attr
associativeArrayKey = r'(\$[\w]+\[(.+?)\]\[(.+?)\])' #......................... $_SESSION["company"]["id"]
arrayKey = r'(\$[\w]+\[(.+?)\])' #............................................. $aDados["nome"] 
variable = r"(\$[\w]+)" #...................................................... $idExample 
functionCall = r'([\w]+\((.+?)\))' #........................................... functionCall($key)
jsonEncodeCall = r'(json_encode\((.+?)\))' #................................... json_encode($key)
namespaceFunctionCall = r'(\\[\w]+\\[\w]+\((.+?)\))' #..........................\Api\get($id)
word = r"(^(\w+)$)" #.......................................................... api 
urlMatch = r'("(.*?),)'
urlVarMatch = r'"(.*?);'

# call types
callApiLine = r'callApi\('
callApiArrayLine = r'callApi\(\['
callApiGetParams = r'callApi\((.*),(.*),(.*)\)'
callApiVariable = r'callApi\(\$\w+,'
internalApiCall = r'\\Internal\\Api::call'
callType = callApiLine

# main pattern
pattern = re.compile(r'((Enum\\[\w]+::[\w]+)|([\w]+::\$[\w]+)|(\\[\w]+::\$[\w]+)|([\w]+\((.+?)\))|(\$[\w]+\[(.+?)\]\[(.+?)\])|(\$[\w]+\[(.+?)\])|(\$[\w]+->[\w]+(->[\w]+)+)|(\$[\w]+->[\w]+)|([\w]+)|(\$[\w]+))')

validMethods = ['"GET"', '"POST"', '"PUT"', '"DELETE"'] # methods to be used in the api call

timestamp = f"// ok {datetime.now().strftime('%d%m%Y')}"

phpRequires = '<?php\n\n'
mockData = ""

dictSubstitutions = {
    variable: r'$textVar',
    jsonEncodeCall: r'json_encode($array)',
    arrayKey: r'$aDados["key"]',
    classAttribute: r'$aDados["attr"]',
    enumStaticReference: r'$aDados["enum"]',
    r'(\\*?\w+::\$\w+)': r'$idExample',
    scopeResolutionOperator: r'$idExample'}

dictMockData = {
    '$aDados': '[]',
    '$aDados["key"]': '"test"',
    '$aDados["attr"]': '"value"',
    '$aDados["enum"]': '"597"',
    '$array': "['key' => 'value']",
    '$idExample': '"999999"',
    '$textVar': '"text"'
}

# eg. param: 'callApi("api/eg/auth/$id", null, "GET")' 
def modifyParams(urlLine, overwriteUrl=0):
    # group params #
    apiCall = re.search(callApiGetParams, urlLine)
    if bool(apiCall):
        url = overwriteUrl if overwriteUrl else modifyUrlString(apiCall.group(1).strip())
        body = apiCall.group(2).strip()
        method = apiCall.group(3).strip()
    
        url = repr(url).strip("'") # prevent from breaking patterns like \Auth::$idExample
        url = r'{url}'.format(url=url) 
        body = repr(body).strip("'") # prevent from breaking patterns like \Auth::$idExample
        body = r'{body}'.format(body=body)
        
        if method not in validMethods:
            return 0

        if ("null" in body):
            newValue = re.sub(r'callApi\((.+)\);', f'{internalApiCall}({method}, {url});', urlLine)
        else:
            newValue = re.sub(r'callApi\((.+)\);', f'{internalApiCall}({method}, {url}, {body});', urlLine)
    else:
        return 0

    return newValue

# eg. param: "api/eg/auth/$id"    
def modifyUrlString(url):
    if "?" in url: # ignoring cases with ? in the url string
        return 0
    # get url patterns
    newUrl = [x.group() for x in re.finditer(pattern, url)]
    # remove first two params from url
    del newUrl[:2]
    parsedUrl = "["
    for pos in newUrl:
        if re.match(word, pos):
            parsedUrl += f'"{pos}", '
            continue
        parsedUrl += f"{pos}, "
    # remove space and last comma
    parsedUrl = parsedUrl[:-2]
    parsedUrl += "]"
    return str(parsedUrl)

# eg. param: '$url = "api/eg/auth/$id";'
def modifyUrlVar(urlVarLine):
    urlVar = re.search(urlVarMatch, urlVarLine)
    if bool(urlVar):
        url = re.search(urlVarMatch, urlVarLine).group(1)
        return modifyUrlString(url)
    return 0


def findApiCalls(fileList):
    filesNotModified = []
    callsNotModified = 0
    print("\n")

    if bool(fileList) == False:
        print("[ERROR] List with files to edit not found. Please, run 'file search' first.")
        return

    # search filenames in current directory
    for fileName in fileList:
        # read file #
        with open (fileName, "r", encoding="utf8") as fileRead:
            fileReadList = [this.rstrip('\n') for this in fileRead]
        newFile = []
        # walk through file #
        for line in fileReadList:
            # found api call #
            if bool(re.search(callApiLine, line)):
                # skip cases
                if bool(re.search('//', line) or re.search('#', line) or re.search(callApiArrayLine, line) or re.search(namespaceFunctionCall, line)):
                    newFile.append(line)
                    callsNotModified += 1
                    continue

                # url passed as variable in api call #
                if bool(re.search(callApiVariable, line)):
                    if (bool(re.search(r'(\$[\w]+) = (.+?);', newFile[-1])) and re.search(r'callApi\((\$[\w]+)', line).group(1) in newFile[-1]):
                        newUrl = modifyUrlVar(newFile[-1])
                        if bool(newUrl):
                            newLine = modifyParams(line, newUrl)
                            if bool(newLine):
                                newFile[-1] = newLine
                                continue
                            else:
                                callsNotModified += 1
                        else:
                            callsNotModified += 1
                    newFile.append(line)
                    continue
                
                # url passed as string inside api call #
                if bool(re.search(r'callApi\("(.+?),', line)):
                    newLine = modifyParams(line)
                    if bool(newLine):
                        newFile.append(newLine)
                        continue
                    else:
                        callsNotModified += 1
            
            newFile.append(line)
            re.purge()  
            
        # if file was not modified, skip save, append to list #
        if fileReadList == newFile:
            filesNotModified.append(fileName)
            continue     

        # save file #
        with open(fileName, 'w', encoding="utf8") as fileSave:
            for position in newFile:
                fileSave.write("%s\n" % position)

        print(f"\n[OK] -> {fileName}")
        progressBar(fileList.index(fileName), len(fileList))
        
    if (callsNotModified > 0):
        print("\n[TOTAL UNMODIFIED CALLS]: %d" % callsNotModified)

    if bool(filesNotModified):
        print("\n[WARNING] Some files were skipped:")
        for name in filesNotModified:
            print(f"[FILE]: {name}")

    progressBar(1, 1)

def listApiCalls(fileList):
    global mockData
    if mockData == "":
        mockData = generateMockData()
    newFile = [phpRequires, mockData, timestamp]

    for fileName in fileList:
        with open (fileName, "r", encoding="utf8") as fileRead:
            fileReadList = [this.rstrip('\n') for this in fileRead]
        newFile.append(f"\n# ARQUIVO: # {fileName}")
        for line in fileReadList:
            if bool(re.search(internalApiCall, line)):
                newLine = re.sub(r'\$[\w]+ = ', '', (line))
                newFile.append(substVars(newLine))
        if (bool(fileName)):
            print(f"\n[OK] -> {fileName}")
            progressBar(fileList.index(fileName), len(fileList))
    with open(dump, "a", encoding="utf8") as dumpObj:
        dumpObj.write(re.sub(r"[\t]*", "", "\n".join(map(str, newFile))))
    progressBar(1, 1)

def substVars(line):
    for key, value in dictSubstitutions.items():
        if bool(re.search(key, line)):
            line = re.sub(key, value, line)
    return line

def generateMockData():
    global mockData
    for key, value in dictMockData.items():
        mockData += f"{key} = {value};\n"
    return mockData
    

def runAll(fileDict):
    try:
        searchFiles(fileDict)
        findApiCalls(fileList)
        listApiCalls(fileList)
    except:
        print("DEU RUIM!!!")

def searchFiles(fileDict):
    global fileList
    fileList = []
    filenamesDictionary = open(fileDict, "r", encoding="utf8")
    filenamesDictionary = [s.strip() for s in filenamesDictionary]
    print("\n[SEARCHING FILES]:")
    for fileName in filenamesDictionary:
        fileDir = f"{currentDir}/{fileName}"
        thisFile = Path(fileDir)
        if thisFile.is_file():
            print(f"\n[OK] -> {fileDir}")
            fileList.append(fileName)
        else:
            print(f"\n[NOT FOUND] -> {fileDir}")
        progressBar(filenamesDictionary.index(fileName), len(filenamesDictionary))
    progressBar(1, 1)

def progressBar(current, total, bar_length=63):
    percent = float(current) / total
    hashes = '#' * int(round(percent * bar_length))
    spaces = '-' * (bar_length - len(hashes))
    print(f"\r[{hashes + spaces}] {int(round(percent * 100))}%", end="\r")
    time.sleep(0.15)


## begin ##
print("_________________________________________________________________")
print("    _   _                                  ____                  ")
print("    /  /|                    /             /   )          /      ")
print("---/| /-|----__----__----__-/----__-------/__ /-----__---/----__-")
print("  / |/  |  /   ) /   ) /   /   /   )     /    )   /   ) /   /   )")
print("_/__/___|_(___(_/___/_(___/___(___(_____/____/___(___(_/___(___(_")
print("\n_____________________________________________________________"+appVersion)
print(f'\ncurrent dir: {currentDir}')
print("_________________________________________________________________")


while(selection):
    print("\nopt:")
    print("[0] exit")
    print("[1] search")
    print("[2] edit")
    print("[3] list")
    print("[4] MANDAR BALA")

    selection = input("choose: ")
    
    if (selection == "0"):
        sys.exit()
    elif (selection == "1"):
        searchFiles(fileDict)
        print("\n_________________________________________________________________")

    elif (selection == "2"):
        findApiCalls(fileList)

    elif (selection == "3"):
        listApiCalls(fileList)
        
    elif (selection == "4"):
        runAll(fileDict)
## end ##
