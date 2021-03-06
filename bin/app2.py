import web
import sqlite3
import os
import subprocess
from datetime import datetime
from collections import OrderedDict

urls = (
    '/', 'Index',
    '/scout', 'Add',
    '/check', 'Check',
    '/saved', 'Saved',
    '/view', 'View',
    '/update', 'Update',
    '/reset', 'Reset',
    '/export', 'Export'
)

app = web.application(urls, globals())
render = web.template.render('templates/', base="layout", globals={'sqlite3':sqlite3, 'web':web, 'str':str, 'int':int})

checkbox = {1:1, 'on':1, None:0}

def totalscore(scorelist):
    ret = 0
    for item in scorelist:
        ret+=int(item)
    return ret

def teamscore(scorelist):
    ret = ""
    for i in range(0, 9):
        ret+=scorelist[i]+", "
    ret+=scorelist[9]
    return ret

def autonomous(digit):
    if digit:
        return 1
    else: return 0
    
def getscore(scorelist):
    line_bonus = int(scorelist[0][0])
    scorelist = list(scorelist[0])
    scorelist = scorelist[1:]
    score = 0
    for i in range(0, len(scorelist)):
        if i in range(0, 3):
            score+=15*int(scorelist[i])
        elif i in range(3, 6):
            score+=10*int(scorelist[i])
        else:
            score+=5*int(scorelist[i])
    score+=(30*line_bonus)
    return score
    
def roundlimit(team, emptyround):
    roundlimits = 0
    for i in range(1, 6):
        test = web.ctx.c.execute("SELECT * FROM round_stat WHERE round_number=:i and team_id=:team", {'i':i, 'team':int(team)}).fetchone()
        if not test:
            if i < emptyround:
                web.ctx.c.execute("INSERT INTO round_stat VALUES (NULL, :i, :team, 0, 0, 0, 0, 0, 0, 0, 0, 0)", {'i':i, 'team':team})
                scoreid = web.ctx.c.execute("SELECT id FROM round_stat WHERE team_id=:team AND round_number=:i", {'team':int(team), 'i':i}).fetchone()
                web.ctx.c.execute('UPDATE full_team SET round'+str(i)+'_id=:roundid WHERE id=:team', {'roundid':int(scoreid[0]), 'team':int(team)})
                web.ctx.c.execute('UPDATE base_team SET scoreRD'+str(i)+'=:score', {'score':0})
                web.ctx.conn.commit()
                roundlimit(team, emptyround+1)
            for j in range(i, 6):
                test = web.ctx.c.execute("SELECT * FROM round_stat WHERE round_number=:i and team_id=:team", {'i':j, 'team':int(team)}).fetchone()
                if test:
                    emptyround = j
                    roundlimit(team, emptyround)
                if not test and j == 5:
                    break
            pass
        else:
            roundlimits+=1
    return roundlimits
    
def filldatalist(rankdict):
    roundlimits = 0
    datalist = []
    teamname = ""
    averagescore = 0
    blocking = 0
    ramp = 0
    defense = 0
    autonomous = 0
    zeros = 0
    for rank in rankdict:
        datalist.append(str(rank))
        team = rankdict.get(rank)
        averagescore = 0
        for i in range(1, roundlimit(team, 0)+1):
            if int(web.ctx.c.execute("SELECT scoreRD"+str(i)+" FROM base_team WHERE id=:team", {'team':team}).fetchone()[0]) == 0:
                print "we got zero"
                zeros+=1
                
            averagescore += int(web.ctx.c.execute("SELECT scoreRD"+str(i)+" FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
            if i == roundlimit(team, 0) and zeros != i:
                averagescore = averagescore/(i-zeros)
            elif i == zeros and i == roundlimit(team, 0):
                averagescore = averagescore/i
        datalist.append(str(team))
        teamname = str(web.ctx.c.execute("SELECT name FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
        datalist.append(str(teamname))
        datalist.append(str(averagescore))
        blocking = int(web.ctx.c.execute("SELECT blocking FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
        datalist.append(str(blocking))
        ramp = int(web.ctx.c.execute("SELECT ramp FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
        datalist.append(str(ramp))
        defense = int(web.ctx.c.execute("SELECT defense FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
        datalist.append(str(defense))
        autonomous = int(web.ctx.c.execute("SELECT autonomous FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
        datalist.append(str(autonomous))
    return datalist
            
def add_to_db(rounds, team, team_score, team_rank, scorelist):
    scorelist = list(scorelist)
    score = getscore(scorelist)
    rounds=int(rounds[0])
    web.ctx.c.executemany('''INSERT INTO round_stat VALUES (NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', team_score)
    web.ctx.c.execute('''UPDATE round_stat SET round_number=:round WHERE team_id=:team AND round_number IS NULL''', {'round':rounds, 'team':int(team[0][0])})
    scoreid = web.ctx.c.execute("SELECT id FROM round_stat WHERE team_id=:team AND round_number=:i", {'team':int(team[0][0]), 'i':rounds}).fetchone()
    if rounds == 1:
        web.ctx.c.execute('''INSERT INTO base_team 
                             VALUES (:baseid, :teamname, :score, null, null, null, null, :blocking, :ramp, :defense, :autonomous)''', {'baseid':team_rank[0][0], 'teamname':team[0][1], 'score':score, 'blocking':team_rank[0][1], 'ramp':team_rank[0][2], 'defense':team_rank[0][3], 'autonomous':autonomous(team_rank[0][4])})
    else:
        ranks = web.ctx.c.execute('''SELECT blocking, ramp, defense, autonomous FROM base_team WHERE id=:team''', {'team':int(team[0][0])}).fetchone()
        ranks = list(ranks)
        team_ranks = list(team_rank[0])
        team_ranks[1] = (int(team_ranks[1])+int(ranks[0]))/2
        team_ranks[2] = (int(team_ranks[2])+int(ranks[1]))/2
        team_ranks[3] = (int(team_ranks[3])+int(ranks[2]))/2
        if ranks[3] == 1:
            team_ranks[4] = 1
        web.ctx.c.execute('''UPDATE base_team SET blocking=:blocking, ramp=:ramp, defense=:defense, autonomous=:autonomous
                             WHERE
                             id=:team''', {'blocking':team_ranks[1], 'ramp':team_ranks[2], 'defense':team_ranks[3], 'autonomous':team_ranks[4], 'team':int(team[0][0])})
    rankid = web.ctx.c.execute("SELECT id FROM base_team WHERE id=:team", {'team':int(team[0][0])}).fetchone()
    full_team = [(int(team[0][0]), rankid[0], scoreid[0]), ]
    if rounds == 1:
        web.ctx.c.executemany('''INSERT INTO full_team VALUES (?, ?, ?, null, null, null)''', full_team)
    elif rounds == 2:
        web.ctx.c.execute('''UPDATE base_team SET scoreRD2=:score''', {'score':score})
        web.ctx.c.execute('''UPDATE full_team SET round2_id=:roundid WHERE id=:team''', {'roundid':full_team[0][2], 'team':full_team[0][0]})#'''INSERT INTO full_team VALUES (?, ?, null, ?, null, null)''', full_team)
    elif rounds == 3:
        web.ctx.c.execute('''UPDATE base_team SET scoreRD3=:score''', {'score':score})
        web.ctx.c.execute('''UPDATE full_team SET round3_id=:roundid WHERE id=:team''', {'roundid':full_team[0][2], 'team':full_team[0][0]})#'''INSERT INTO full_team VALUES (?, ?, null, null, ?, null)''', full_team)
    elif rounds == 4:
        web.ctx.c.execute('''UPDATE base_team SET scoreRD4=:score''', {'score':score})
        web.ctx.c.execute('''UPDATE full_team SET round4_id=:roundid WHERE id=:team''', {'roundid':full_team[0][2], 'team':full_team[0][0]})#'''INSERT INTO full_team VALUES (?, ?, null, null, null, ?)''', full_team)
    else:
        web.ctx.c.execute('''UPDATE base_team SET scoreRD5=:score''', {'score':score})
        web.ctx.c.execute('''UPDATE full_team SET round5_id=:roundid WHERE id=:team''', {'roundid':full_team[0][2], 'team':full_team[0][0]})#'''INSERT INTO full_team VALUES (?, ?, null, null, null, ?)''', full_team)
    web.ctx.conn.commit()
    print "DONE"
    web.seeother('/')
    return

class Index(object):
    def GET(self):
        return render.index()

class Add(object):
    def GET(self):
        return render.scout_form2()
        
class Check(object):
    def GET(self):
        web.seeother('/')
        
    def POST(self):
        form = web.input(yes=None, rounds=None, team1=None, teamname=None, id13=None, id23=None, id33=None, id12=None, id22=None, id32=None, id11=None, id21=None, id31=None, linebonus=None, blocking=None, ramp=None, defense=None, autonomous=None)
        team_score = [(form.team1, form.id13, form.id23, form.id33, form.id12, form.id22, form.id32, form.id11, form.id21, form.id31), ]
        scoredata = [(form.id13, form.id23, form.id33, form.id12, form.id22, form.id32, form.id11, form.id21, form.id31), ]
        scorelist = [(form.linebonus, form.id13, form.id23, form.id33, form.id12, form.id22, form.id32, form.id11, form.id21, form.id31)]
        team_rank = [(eval(form.team1), eval(form.blocking), eval(form.ramp), eval(form.defense), checkbox.get(form.autonomous)), ]
        x = checkbox.get(form.autonomous)
        if not x:
            x = 0
        rankingdata = [(form.blocking, form.ramp, form.defense, form.autonomous), ]
        team = [(int(form.team1), str(form.teamname)), ]
        if form.yes:
            add_to_db((form.rounds, ), team, team_score, team_rank, scorelist)
        elif not form.yes and not form.team1:
            web.seeother('/scout')
        else: pass
        return render.check(rounds=form.rounds, team=team, scoringdata=scoredata, rankdata=rankingdata, linebonus=form.linebonus)

class Saved(object):
    def GET(self):
        return render.saved()
        
class View(object):
    def GET(self):
        teams = web.ctx.c.execute("SELECT id FROM full_team").fetchall()
        return render.view_select(teamlist=teams)
        
    def POST(self):
        roundlimits = 0
        score = [0, 0, 0, 0, 0]
        ringnumber = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        topnumberscore = 0
        midnumberscore = 0
        botnumberscore = 0
        form = web.input(teamnum=None)
        if "export" in form.teamnum:
            return web.seeother('/export')
        elif type(eval(form.teamnum)) is int:
            team = [eval(form.teamnum)]
        else:
            team = eval(form.teamnum)
        roundlimits = roundlimit(int(team[0]), 0)
        print roundlimits
        for i in range(1, roundlimits+1):
            real_scoreRD = web.ctx.c.execute("SELECT scoreRD"+str(i)+" FROM base_team WHERE id=:team", {'team':int(team[0])}).fetchone()
            score[i] = int(real_scoreRD[0])
            print i
            scoreRD = web.ctx.c.execute("SELECT * FROM round_stat WHERE team_id=:team AND round_number=:i", {'i':i, 'team':int(team[0])}).fetchall()
            if not scoreRD:
                break
            scoreRD = scoreRD[0]
            for i in range(3, 6):
                ringnumber[i-3]+=scoreRD[i]
            for i in range(6, 9):
                ringnumber[i-3]+=scoreRD[i]
            for i in range(9, 12):
                ringnumber[i-3]+=scoreRD[i]
        teamname = web.ctx.c.execute("SELECT name FROM base_team WHERE id=:teamnum", {'teamnum':team[0]}).fetchone()
        totalringcount = 0
        for rings in ringnumber:
            totalringcount+=rings
        percents = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        for i in range(0, 9):
            if totalringcount != 0:
                percents[i] = ringnumber[i]*100/totalringcount
        ranklist = [0, 0, 0, 0]
        ranks = web.ctx.c.execute('''SELECT blocking, ramp, defense, autonomous FROM base_team WHERE id=:team''', {'team':team[0]}).fetchone()
        return render.view_show(teamnum=team, name=teamname, scores=ringnumber, percents=percents, rounds=roundlimits, ranklist=ranks)
        
class Update(object):
    def GET(self):
        return render.update()

class Export(object):
    def GET(self):
        roundlimits = 0
        allteamnum = []
        totalrankscore = float(0)
        averagescore = 0
        blockingscore = 0
        defensescore = 0
        rampscore = 0
        autonomousscore = 0
        teams_rankscores = {}
        allteamnumtuple = web.ctx.c.execute("SELECT id FROM full_team").fetchall()
        for item in allteamnumtuple:
            allteamnum.append(item[0])
        for team in allteamnum:
            totalrankscore = float(0)
            averagescore = 0
            blockingscore = 0
            defensescore = 0
            rampscore = 0
            autonomousscore = 0
            roundlimits = roundlimit(team, 0)
            for i in range(1, roundlimits+1):
                averagescore += 7*int(web.ctx.c.execute("SELECT scoreRD"+str(i)+" FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])/16
                if i == roundlimits:
                    averagescore = averagescore/roundlimits
            blockingscore = 46*int(web.ctx.c.execute("SELECT blocking FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
            defensescore = 46*int(web.ctx.c.execute("SELECT defense FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
            rampscore = 46*int(web.ctx.c.execute("SELECT ramp FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
            autonomousscore = 230*int(web.ctx.c.execute("SELECT autonomous FROM base_team WHERE id=:team", {'team':team}).fetchone()[0])
            totalrankscore = float((averagescore*.75)+(blockingscore*.1)+(defensescore*.1)+(rampscore*.01)+(autonomousscore*.04))
            teams_rankscores[int(totalrankscore)] = team
        teams_rankscores = OrderedDict(sorted(teams_rankscores.items(), key=lambda t: t[0], reverse=True))
        datalist = filldatalist(teams_rankscores)
        return render.export(datalisted=datalist)
        
class Reset(object):
    def GET(self):
        subprocess.call(["mv", "db/scouting.db", "db/scouting"+str(datetime.now())+".db"])
        os.system("sqlite3 db/scouting.db < db/db1.sql")
        return render.reset()
        
def my_loadhook():
    web.ctx.conn = sqlite3.connect('db/scouting.db')
    web.ctx.c = web.ctx.conn.cursor()

if __name__ == "__main__":
    app.add_processor(web.loadhook(my_loadhook))
    app.run()
    
    
