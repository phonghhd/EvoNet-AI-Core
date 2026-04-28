import os
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv("/app/.env", override=True)

logger = logging.getLogger(__name__)

class SecurityKnowledgeGraph:
    def __init__(self):
        """
        Initialize connection to Neo4j database
        """
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not password:
            logger.warning("NEO4J_PASSWORD not set, KG functionality will be limited")
            self.driver = None
            return
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Verify connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """
        Close the database connection
        """
        if self.driver is not None:
            self.driver.close()
    
    def add_cve_node(self, cve_id, description, cvss_score, cwe_ids, affected_software, exploit_maturity, published_date):
        """
        Add a CVE node to the knowledge graph
        """
        if self.driver is None:
            logger.warning("KG driver not initialized, skipping add_cve_node")
            return False
        
        try:
            with self.driver.session() as session:
                session.run("""
                MERGE (c:CVE {id: $cve_id})
                SET c.description = $description,
                    c.cvss_score = $cvss_score,
                    c.exploit_maturity = $exploit_maturity,
                    c.published_date = $published_date
                """, 
                cve_id=cve_id,
                description=description,
                cvss_score=float(cvss_score) if cvss_score else 0.0,
                exploit_maturity=exploit_maturity,
                published_date=published_date)
                
                # Add CWE relationships
                for cwe_id in cwe_ids:
                    session.run("""
                    MERGE (w:CWE {id: $cwe_id})
                    MERGE (c:CVE {id: $cve_id})
                    MERGE (c)-[:HAS_WEAKNESS]->(w)
                    """, cve_id=cve_id, cwe_id=cwe_id)
                
                # Add affected software relationships
                for software in affected_software:
                    session.run("""
                    MERGE (s:Software {name: $software})
                    MERGE (c:CVE {id: $cve_id})
                    MERGE (c)-[:AFFECTS]->(s)
                    """, cve_id=cve_id, software=software)
            
            logger.debug(f"Added CVE {cve_id} to knowledge graph")
            return True
        except Exception as e:
            logger.error(f"Error adding CVE {cve_id} to KG: {e}")
            return False
    
    def add_defense_skill(self, skill_id, description, model_used, source_cve, confidence_score=0.8):
        """
        Add a defense skill node to the knowledge graph
        """
        if self.driver is None:
            logger.warning("KG driver not initialized, skipping add_defense_skill")
            return False
        
        try:
            with self.driver.session() as session:
                session.run("""
                MERGE (d:DefenseSkill {id: $skill_id})
                SET d.description = $description,
                    d.model_used = $model_used,
                    d.source_cve = $source_cve,
                    d.confidence_score = $confidence_score
                """,
                skill_id=skill_id,
                description=description,
                model_used=model_used,
                source_cve=source_cve,
                confidence_score=float(confidence_score))
            
            logger.debug(f"Added defense skill {skill_id} to knowledge graph")
            return True
        except Exception as e:
            logger.error(f"Error adding defense skill {skill_id} to KG: {e}")
            return False
    
    def link_defense_to_cve(self, skill_id, cve_id, relationship_type="MITIGATES"):
        """
        Create a relationship between a defense skill and a CVE
        """
        if self.driver is None:
            logger.warning("KG driver not initialized, skipping link_defense_to_cve")
            return False
        
        try:
            with self.driver.session() as session:
                session.run(f"""
                MATCH (d:DefenseSkill {{id: $skill_id}})
                MATCH (c:CVE {{id: $cve_id}})
                MERGE (d)-[r:{relationship_type}]->(c)
                SET r.created_at = timestamp()
                """, skill_id=skill_id, cve_id=cve_id)
            
            logger.debug(f"Linked defense skill {skill_id} to CVE {cve_id} with {relationship_type}")
            return True
        except Exception as e:
            logger.error(f"Error linking defense skill {skill_id} to CVE {cve_id}: {e}")
            return False
    
    def get_defenses_for_cve(self, cve_id):
        """
        Get defense skills that mitigate a specific CVE
        """
        if self.driver is None:
            logger.warning("KG driver not initialized, returning empty list")
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (d:DefenseSkill)-[r:MITIGATES]->(c:CVE {id: $cve_id})
                RETURN d.id as skill_id, 
                       d.description as description,
                       d.model_used as model_used,
                       d.confidence_score as confidence_score,
                       r.created_at as created_at
                ORDER BY d.confidence_score DESC
                """, cve_id=cve_id)
                
                defenses = []
                for record in result:
                    defenses.append({
                        'skill_id': record['skill_id'],
                        'description': record['description'],
                        'model_used': record['model_used'],
                        'confidence_score': record['confidence_score'],
                        'created_at': record['created_at']
                    })
                return defenses
        except Exception as e:
            logger.error(f"Error retrieving defenses for CVE {cve_id}: {e}")
            return []
    
    def get_related_cves(self, cve_id, relationship_type="HAS_WEAKNESS", depth=2):
        """
        Get related CVEs based on shared weaknesses or software
        """
        if self.driver is None:
            logger.warning("KG driver not initialized, returning empty list")
            return []
        
        try:
            with self.driver.session() as session:
                # Query for CVEs sharing CWEs or affected software
                result = session.run(f"""
                MATCH (c:CVE {{id: $cve_id}})-[r1:{relationship_type}]->(node)<-[r2:{relationship_type}]-(related:CVE)
                WHERE related.id <> $cve_id
                RETURN DISTINCT related.id as cve_id, 
                       collect(distinct node.id) as via_nodes,
                       count(*) as connection_strength
                ORDER BY connection_strength DESC
                LIMIT 20
                """, cve_id=cve_id)
                
                related = []
                for record in result:
                    related.append({
                        'cve_id': record['cve_id'],
                        'via_nodes': record['via_nodes'],
                        'connection_strength': record['connection_strength']
                    })
                return related
        except Exception as e:
            logger.error(f"Error retrieving related CVEs for {cve_id}: {e}")
            return []

# Global instance for easy access
kg_instance = None

def get_kg_instance():
    global kg_instance
    if kg_instance is None:
        kg_instance = SecurityKnowledgeGraph()
    return kg_instance

def close_kg():
    global kg_instance
    if kg_instance is not None:
        kg_instance.close()
        kg_instance = None