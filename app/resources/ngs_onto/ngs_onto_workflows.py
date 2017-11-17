from app import app, dbconAg,dedicateddbconAg
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with #filters data according to some fields
from flask_security import current_user
from flask import jsonify
from app.utils.queryParse2Json import parseAgraphStatementsRes,parseAgraphQueryRes

#from app.models.models import Study
#from flask.ext.security import current_user, login_required, roles_required
from config import obo,localNSpace,protocolsTypes,processTypes,processMessages
from franz.openrdf.vocabulary.rdf import RDF
from franz.openrdf.vocabulary.xmlschema import XMLSchema
from franz.openrdf.query.query import QueryLanguage
from franz.openrdf.model import URI


#Defining post arguments parser
workflow_post_parser = reqparse.RequestParser()
workflow_post_parser.add_argument('workflow_id', dest='workflow_id', type=str, required=True, help="Workflow id")
workflow_post_parser.add_argument('protocol_ids', dest='protocol_ids', type=str, required=True, help="Protocol id list")

#Create pipeline and defining workflow order on pipeline
pipeline_post_parser = reqparse.RequestParser()
pipeline_post_parser.add_argument('workflow_id', dest='workflow_id', type=str, required=True, help="Workflow id")
pipeline_post_parser.add_argument('step', dest='step', type=str, required=True, help="workflow order in pipeline")

#Defining get arguments parser
workflow_get_parser = reqparse.RequestParser()
workflow_get_parser.add_argument('workflow_id', dest='workflow_id', type=str, required=True, help="Workflow id")



class NGSOnto_WorkflowListPipelineResource(Resource):
	
	def get(self, id,id1):
		
		#Agraph
		pipelineStr = localNSpace+"projects/"+str(id)+"/pipelines/"+str(id1)	
		
		
		#queryString = "SELECT ?execStep ?workflowURI  WHERE {<"+pipelineStr+"> obo:NGS_0000076 ?execStep. ?execStep obo:NGS_0000079 ?workflowURI.}"
		queryString = "SELECT DISTINCT ?proc3 ?pip2 ?execStep ?workflowURI WHERE {{<"+pipelineStr+"> obo:BFO_0000051 ?proc3. ?pip2 obo:BFO_0000051 ?proc3; obo:NGS_0000076 ?execStep. ?proc3 obo:NGS_0000081 ?procIndex3. ?execStep obo:NGS_0000079 ?workflowURI; obo:NGS_0000081 ?procIndex3.} UNION {<"+pipelineStr+"> obo:BFO_0000051 ?proc1. ?proc1 obo:RO_0002233 ?inputs1. ?proc2 obo:RO_0002234 ?inputs1; obo:NGS_0000081 ?procIndex2. ?pip2 obo:BFO_0000051 ?proc2; obo:BFO_0000051 ?proc3. ?proc3 obo:NGS_0000081 ?procIndex3. ?pip2 obo:NGS_0000076 ?execStep. ?execStep obo:NGS_0000079 ?workflowURI; obo:NGS_0000081 ?stepIndex. FILTER  (?procIndex3 <= ?procIndex2 && ?stepIndex = ?procIndex3). }} ORDER BY ?pip2 ASC(?procIndex3)"

		tupleQuery = dbconAg.prepareTupleQuery(QueryLanguage.SPARQL, queryString)
		result = tupleQuery.evaluate()
		jsonResult=parseAgraphQueryRes(result,["execStep","workflowURI"])
		
		result.close()

		return jsonResult,200

	def post(self, id,id1):

		#Agraph

		args = pipeline_post_parser.parse_args()

		wkflid = args.workflow_id
		prtjctid = id
		pplid = id1
		step = args.step

		wkflid = wkflid.split(',')
		step = step.split(',')


		#check if workflow is on pipeline

		pipelineStr = localNSpace+"projects/"+str(prtjctid)+"/pipelines/"+str(pplid)
		#workflowStr = localNSpace+"workflows/"+str(wkflid)

		queryString = "SELECT ?execStep (STR(?intstep) as ?step) WHERE {<"+pipelineStr+"> obo:NGS_0000076 ?execStep. ?execStep obo:NGS_0000081 ?intstep.}"
		tupleQuery = dbconAg.prepareTupleQuery(QueryLanguage.SPARQL, queryString)
		result = tupleQuery.evaluate()
		jsonResult=parseAgraphQueryRes(result,["execStep","step"])
		result.close()

		print jsonResult
		

		for result in jsonResult:
			aux1= result["execStep"]
			aux2= result["step"]
			#print "AQUI"
			#print aux1
			#print aux2
			#print step
			step_converted = map(int, step)
			#print step_converted
			#print int(aux2.replace('"', ''))

			if int(aux2.replace('"', '')) in step_converted or int(aux2.replace('"', '')) > max(step_converted):
				#print "ENTROU", aux1
				toremove=dbconAg.createURI(aux1)
				dbconAg.remove(None,None,toremove)
				dbconAg.remove(toremove,None,None)
		
		'''if len(jsonResult) > 0:
			return 409
		else:'''
		counter = -1
		for i in wkflid:	
			counter+=1
			#add new workflow
			exStepType=dbconAg.createURI(namespace=obo, localname="NGS_0000074")
			#workflowURI = dbconAg.createURI(namespace=localNSpace+"user/"+args.user_id+"/studies/", localname="study_"+str(id2)+"/pipelines/pipeline_"+str(id3)+"/workflows/workflow_"+str(numberOfWorkflows+1))
			workflowURI = dbconAg.createURI(namespace=localNSpace, localname="workflows/"+str(i))
			
			executeRel=dbconAg.createURI(namespace=obo, localname="NGS_0000076")
			pipelineURI = dbconAg.createURI(namespace=localNSpace+"projects/", localname=str(prtjctid)+"/pipelines/"+str(pplid))
			exStepURI = dbconAg.createURI(namespace=localNSpace+"projects/", localname=str(prtjctid)+"/pipelines/"+str(pplid)+"/step/"+str(step[counter]))
			indexInt = dbconAg.createLiteral((step[counter]), datatype=XMLSchema.INT)
			indexProp = dbconAg.createURI(namespace=obo, localname="NGS_0000081")
			hasWorkflRel = dbconAg.createURI(namespace=obo, localname="NGS_0000079")
			
			dbconAg.add(exStepURI, RDF.TYPE, exStepType)
			stmt1 = dbconAg.createStatement(exStepURI, indexProp, indexInt)
			dbconAg.add(stmt1)
			#link pipeline to step
			dbconAg.add(pipelineURI, executeRel, exStepURI)
			#add workflow + link to step
			workflowType= dbconAg.createURI(namespace=obo, localname="OBI_0500000")
			dbconAg.add(workflowURI, RDF.TYPE, workflowType)
			dbconAg.add(exStepURI, hasWorkflRel, workflowURI)
		
		return 201

	def delete(self, id):
		pass


class NGSOnto_ProtocolWorkflowResource(Resource):    
	
	def get(self):
		args=workflow_get_parser.parse_args()

		#Agraph
		workflowsid=args.workflow_id
		workflowURI = localNSpace+"workflows/"+str(workflowsid)


		queryString = "SELECT ?protocol ?index WHERE { <"+workflowURI+"""> obo:NGS_0000078 ?step.
						?step obo:NGS_0000077 ?protocol;
						obo:NGS_0000081 ?index.}"""
		tupleQuery = dbconAg.prepareTupleQuery(QueryLanguage.SPARQL, queryString)
		result = tupleQuery.evaluate()
		jsonResult=parseAgraphQueryRes(result,["index","protocol"])
		print jsonResult

		result.close()

		return jsonResult,200


	def post(self):

		args=workflow_post_parser.parse_args()

		protocol_ids = args.protocol_ids.split(',')
		workflow_id = args.workflow_id    

		for p_id in protocol_ids:

			print p_id

			protocolURI = dbconAg.createURI(namespace=localNSpace, localname="protocols/"+str(p_id))
			print protocolURI

			hasStep = dbconAg.createURI(namespace=obo, localname="NGS_0000078")
			workflowURI = dbconAg.createURI(namespace=localNSpace, localname="workflows/"+str(workflow_id))
			statements = dbconAg.getStatements(workflowURI, hasStep, None)
			jsonResult=parseAgraphStatementsRes(statements)
			statements.close()
			numberOfProtocols=len(jsonResult)

			protocolStepType = dbconAg.createURI(namespace=obo, localname="NGS_0000075")
			protocStepUri = dbconAg.createURI(namespace=localNSpace, localname="workflows/"+str(workflow_id)+"/step/"+str(numberOfProtocols+1))
			indexProp = dbconAg.createURI(namespace=obo, localname="NGS_0000081")
			indexInt = dbconAg.createLiteral((numberOfProtocols+1), datatype=XMLSchema.INT)
			hasProtocolRel=dbconAg.createURI(namespace=obo, localname="NGS_0000077")

			#add step + index
			dbconAg.add(protocStepUri, RDF.TYPE, protocolStepType)
			stmt1 = dbconAg.createStatement(protocStepUri, indexProp, indexInt)
			dbconAg.add(stmt1)
			#link workflow to step
			dbconAg.add(workflowURI, hasStep, protocStepUri)
			#add protocol + link to step
			dbconAg.add(protocStepUri, hasProtocolRel, protocolURI)

		return 201